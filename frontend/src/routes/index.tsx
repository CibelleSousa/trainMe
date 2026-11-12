import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import gymCss from "../gym.css?url";
import { VoiceOrb } from "../components/VoiceOrb";
import { iniciarNovaSessao, mesclarResultadoDeSessao, textoCompleto } from "../lib/speech-merge";

const SILENCIO_LIMITE_MS = 4000;

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "TrainMe — Registre seu treino por voz" },
      { name: "description", content: "Fale ou digite seu treino na academia e receba a sugestão da próxima carga." },
      { property: "og:title", content: "TrainMe — Registre seu treino por voz" },
      { property: "og:description", content: "Fale ou digite seu treino na academia e receba a sugestão da próxima carga." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "theme-color", content: "#0b0b0c" },
    ],
    links: [{ rel: "stylesheet", href: gymCss }],
  }),
  component: Index,
});

const USER = "Cibelle";

type LoggedSet = { exercise: string; weight_kg: number | null; reps: number };
type Suggestion = {
  acao: string;
  weight_kg: number | null;
  reps_alvo: number | null;
  estagnado: boolean;
  sessoes_sem_progresso: number;
};
type HistoryItem = { id: number; text: string; reply: string; logged: LoggedSet[]; suggestion: Suggestion | null };

export function Index() {
  const [text, setText] = useState("");
  const [listening, setListening] = useState(false);
  const [interim, setInterim] = useState("");
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set());
  const [pendingText, setPendingText] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [speechSupported] = useState(
    () => typeof window !== "undefined" && !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition),
  );
  const [debugEnabled] = useState(
    () => typeof window !== "undefined" && new URLSearchParams(window.location.search).get("debug") === "1",
  );
  const [debugLog, setDebugLog] = useState<string[]>([]);
  const levelRef = useRef(0);
  const stopRef = useRef<() => void>(() => {});
  const manualStopRef = useRef(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const baseRef = useRef(""); // texto de sessões de reconhecimento já fechadas
  const sessaoRef = useRef(""); // texto (substituído, não somado) da sessão atual
  const silencioRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => stopRef.current(), []);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [text]);

  function start() {
    // Não usa getUserMedia: no Chrome Android, disputar o microfone com o
    // próprio motor de reconhecimento de voz trava a transcrição (o orb
    // reage, mas onresult nunca chega). O orb pulsa de forma sintética.
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;

    manualStopRef.current = false;
    baseRef.current = text;
    sessaoRef.current = "";
    let raf = 0, t = 0;

    const limparSilencio = () => {
      if (silencioRef.current) clearTimeout(silencioRef.current);
      silencioRef.current = null;
    };
    const armarSilencio = () => {
      limparSilencio();
      silencioRef.current = setTimeout(() => stopRef.current(), SILENCIO_LIMITE_MS);
    };

    const rec = new SR();
    rec.lang = "pt-BR";
    rec.continuous = true;
    rec.interimResults = true;
    rec.onresult = (e: any) => {
      armarSilencio();
      let fin = "", tmp = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        r.isFinal ? (fin += r[0].transcript) : (tmp += r[0].transcript);
      }
      // No Android cada resultado final costuma vir com o texto acumulado da
      // sessão (não só a palavra nova) — por isso substitui, nunca soma.
      if (fin) sessaoRef.current = mesclarResultadoDeSessao(sessaoRef.current, fin.trim());
      const textoFinal = textoCompleto(baseRef.current, sessaoRef.current);
      setText(textoFinal);
      setInterim(tmp);

      if (debugEnabled) {
        const hora = new Date().toLocaleTimeString("pt-BR", { hour12: false });
        const resultados = [];
        for (let i = 0; i < e.results.length; i++) {
          const r = e.results[i];
          resultados.push(`  [${i}] isFinal=${r.isFinal} "${r[0].transcript}"`);
        }
        const linha = [
          `[${hora}] onresult resultIndex=${e.resultIndex} results.length=${e.results.length}`,
          ...resultados,
          `  baseRef="${baseRef.current}"`,
          `  sessaoRef="${sessaoRef.current}"`,
          `  texto final="${textoFinal}"`,
        ].join("\n");
        setDebugLog((log) => [...log.slice(-19), linha]);
      }
    };
    rec.onerror = (e: any) => {
      if (e.error === "not-allowed" || e.error === "service-not-allowed") {
        manualStopRef.current = true;
        setHistory((h) => [
          ...h,
          { id: Date.now(), text: "", reply: "Não consegui acessar o microfone. Libere a permissão e tente de novo.", logged: [], suggestion: null },
        ]);
      }
    };
    rec.onend = () => {
      // Android/Chrome encerra a sessão sozinho mesmo com continuous=true.
      // Só limpa o estado se foi o usuário (ou o timer de silêncio) quem pediu
      // pra parar; senão, fecha a sessão atual na base e reinicia uma vazia.
      if (manualStopRef.current) {
        limparSilencio();
        cancelAnimationFrame(raf);
        levelRef.current = 0;
        setInterim("");
        setListening(false);
      } else {
        baseRef.current = iniciarNovaSessao(baseRef.current, sessaoRef.current);
        sessaoRef.current = "";
        try {
          rec.start();
        } catch {
          // já reiniciando ou indisponível; deixa o próximo onend tentar de novo
        }
      }
    };
    rec.start();
    armarSilencio();

    const pulse = () => {
      t += 0.05;
      levelRef.current = 0.35 + Math.sin(t) * 0.2 + Math.random() * 0.08;
      raf = requestAnimationFrame(pulse);
    };
    pulse();

    stopRef.current = () => {
      manualStopRef.current = true;
      limparSilencio();
      rec.stop();
    };
    setListening(true);
  }

  async function sendText(valor: string) {
    const texto = valor.trim();
    if (!texto || sending) return;
    setSending(true);
    try {
      const resp = await fetch("/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: texto }),
      });
      const dados = await resp.json();
      const replyText: string = resp.ok ? dados.reply : `Erro: ${dados.detail ?? resp.status}`;
      setHistory((h) => [
        ...h,
        { id: Date.now(), text: texto, reply: replyText, logged: dados.logged ?? [], suggestion: resp.ok ? dados.suggestion ?? null : null },
      ]);
      setPendingText(resp.ok && replyText.toLowerCase().includes("por lado") ? texto : null);
    } catch (erro) {
      setHistory((h) => [
        ...h,
        { id: Date.now(), text: texto, reply: `Erro de conexão: ${erro}`, logged: [], suggestion: null },
      ]);
      setPendingText(null);
    } finally {
      setSending(false);
    }
  }

  function send() {
    if (!text.trim()) return;
    if (listening) stopRef.current();
    const valor = text.trim();
    setText("");
    void sendText(valor);
  }

  function responderLado(porLado: boolean) {
    if (!pendingText) return;
    const complemento = porLado ? ", cada lado" : ", isso já é o total, não é por lado";
    setPendingText(null);
    void sendText(pendingText + complemento);
  }

  const ultima = history[history.length - 1];
  const perguntouLado = !!pendingText && !!ultima && ultima.reply.toLowerCase().includes("por lado");

  function toggleExpand(id: number) {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  function formatarSugestao(s: Suggestion): string {
    const carga = s.weight_kg != null ? `${s.weight_kg}kg` : "peso corporal";
    const reps = s.reps_alvo != null ? `, alvo ${s.reps_alvo} reps` : "";
    const estagnado = s.estagnado ? ` · estagnado há ${s.sessoes_sem_progresso} sessões` : "";
    return `Próxima: ${carga}${reps}${estagnado}`;
  }

  function agruparPorExercicio(logged: LoggedSet[]): { exercise: string; series: string }[] {
    const grupos: { exercise: string; partes: string[] }[] = [];
    for (const s of logged) {
      const carga = s.weight_kg != null ? `${s.weight_kg}kg` : "corporal";
      const parte = `${carga} x${s.reps}`;
      const grupo = grupos.find((g) => g.exercise === s.exercise);
      if (grupo) grupo.partes.push(parte);
      else grupos.push({ exercise: s.exercise, partes: [parte] });
    }
    return grupos.map((g) => ({ exercise: g.exercise, series: g.partes.join(", ") }));
  }

  return (
    <main className="app">
      <header className="top">
        <div className="brand">TRAIN<span>ME</span></div>
        <div className={`chip ${listening ? "live" : ""}`}><i />{listening ? "Ouvindo" : "Pronto"}</div>
      </header>

      <section className={`stage ${history.length > 0 ? "compact" : ""}`}>
        <VoiceOrb levelRef={levelRef} active={listening} />
        {history.length === 0 ? (
          <div className="greet">
            <small>Olá,<b>{USER}</b></small>
            <h1>Vamos <em>treinar?</em></h1>
          </div>
        ) : (
          <div className="greet greet-mini">
            <small>Olá,<b>{USER}</b></small>
          </div>
        )}
        <p className="transcript">{interim || (listening ? "Fale seu treino…" : "")}</p>
      </section>

      {history.length > 0 && (
        <section className="history" aria-label="Histórico do dia">
          {[...history].reverse().map((item, i) => {
            const expandido = expandedIds.has(item.id);
            return (
              <div
                className="history-item"
                role="status"
                key={item.id}
                onClick={() => toggleExpand(item.id)}
              >
                {item.suggestion && <p className="suggestion">{formatarSugestao(item.suggestion)}</p>}
                <p className={`history-reply ${expandido ? "expanded" : ""}`}>{item.reply}</p>
                <span className="toggle-indicator">{expandido ? "ver menos ▲" : "ver mais ▼"}</span>
                {item.logged.length > 0 && (
                  <ul className="sets-list">
                    {agruparPorExercicio(item.logged).map((g) => (
                      <li key={g.exercise}>
                        <b>{g.exercise}</b> — {g.series}
                      </li>
                    ))}
                  </ul>
                )}
                {i === 0 && perguntouLado && (
                  <div className="side-buttons" onClick={(e) => e.stopPropagation()}>
                    <button type="button" onClick={() => responderLado(true)}>Sim, é por lado</button>
                    <button type="button" onClick={() => responderLado(false)}>Não, é o total</button>
                  </div>
                )}
              </div>
            );
          })}
        </section>
      )}

      <footer className="dock">
        <form className="field" onSubmit={(e) => { e.preventDefault(); send(); }}>
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder="Digite seu treino se preferir…"
            aria-label="Treino"
            disabled={sending}
            rows={1}
          />
          <button className="send" disabled={!text.trim() || sending}>{sending ? "Enviando…" : "Enviar"}</button>
        </form>
        {speechSupported ? (
          <>
            <button className={`mic ${listening ? "on" : ""}`} onClick={() => (listening ? stopRef.current() : start())} aria-label={listening ? "Parar gravação" : "Gravar treino"}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><rect x="9" y="2" width="6" height="12" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v4" /></svg>
            </button>
            <span className="hint">{listening ? "Toque para parar" : "Toque para falar"}</span>
          </>
        ) : (
          <span className="hint speech-warning">Seu navegador não tem reconhecimento de voz. Use o campo de texto.</span>
        )}
      </footer>

      {debugEnabled && (
        <pre className="debug-panel" aria-label="Painel de debug da voz">
          {debugLog.length === 0 ? "Sem eventos onresult ainda. Toque no mic e fale." : debugLog.join("\n\n")}
        </pre>
      )}
    </main>
  );
}
