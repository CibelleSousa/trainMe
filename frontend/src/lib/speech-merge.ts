// No Chrome Android, cada onresult final em modo continuous costuma trazer o
// texto ACUMULADO da fala até agora ("supino", "supino reto", "supino reto 3"...),
// não só a palavra nova. Por isso a sessão de reconhecimento precisa ser
// SUBSTITUÍDA pelo resultado mais recente, nunca somada.

/**
 * Funde um novo resultado de reconhecimento com o texto já acumulado na sessão atual.
 * Se o novo resultado começa com o texto atual, é uma atualização (substitui).
 * Se não começa, é uma frase nova dentro da mesma sessão (acrescenta).
 */
export function mesclarResultadoDeSessao(sessaoAtual: string, resultadoNovo: string): string {
  const atual = sessaoAtual.trim();
  const novo = resultadoNovo.trim();
  if (!novo) return atual;
  if (!atual) return novo;
  if (novo.startsWith(atual)) return novo;
  return `${atual} ${novo}`.trim();
}

/** Fecha a sessão atual (move pro texto-base) e devolve a nova base, pra começar uma sessão vazia. */
export function iniciarNovaSessao(base: string, sessaoFechada: string): string {
  const fechada = sessaoFechada.trim();
  if (!fechada) return base.trim();
  const baseAtual = base.trim();
  return baseAtual ? `${baseAtual} ${fechada}` : fechada;
}

/** Texto completo mostrado no campo: base (sessões já fechadas) + sessão atual. */
export function textoCompleto(base: string, sessaoAtual: string): string {
  const b = base.trim();
  const s = sessaoAtual.trim();
  if (!b) return s;
  if (!s) return b;
  return `${b} ${s}`;
}
