import { describe, expect, it } from "vitest";
import { iniciarNovaSessao, mesclarResultadoDeSessao, textoCompleto } from "@/lib/speech-merge";

describe("mesclarResultadoDeSessao", () => {
  it("substitui pelo resultado acumulado em vez de concatenar (caso do Android)", () => {
    let sessao = "";
    sessao = mesclarResultadoDeSessao(sessao, "supino");
    expect(sessao).toBe("supino");

    sessao = mesclarResultadoDeSessao(sessao, "supino reto");
    expect(sessao).toBe("supino reto");

    sessao = mesclarResultadoDeSessao(sessao, "supino reto 3");
    expect(sessao).toBe("supino reto 3");

    sessao = mesclarResultadoDeSessao(sessao, "supino reto 3 10 repetições");
    expect(sessao).toBe("supino reto 3 10 repetições");
  });

  it("acrescenta quando o resultado novo não é continuação do atual", () => {
    const sessao = mesclarResultadoDeSessao("supino reto", "remada serrote");
    expect(sessao).toBe("supino reto remada serrote");
  });

  it("primeiro resultado da sessão vira a sessão inteira", () => {
    expect(mesclarResultadoDeSessao("", "supino")).toBe("supino");
  });

  it("ignora resultado novo vazio", () => {
    expect(mesclarResultadoDeSessao("supino reto", "")).toBe("supino reto");
  });
});

describe("iniciarNovaSessao", () => {
  it("move o texto da sessão fechada pra base", () => {
    expect(iniciarNovaSessao("", "supino reto 3 10 repetições")).toBe("supino reto 3 10 repetições");
  });

  it("junta com a base já existente sem duplicar", () => {
    expect(iniciarNovaSessao("supino reto 3 10 repetições", "")).toBe("supino reto 3 10 repetições");
  });

  it("sessão fechada vazia não altera a base", () => {
    expect(iniciarNovaSessao("supino reto 3 10 repetições", "")).toBe("supino reto 3 10 repetições");
  });
});

describe("fluxo completo com reinício de sessão (Android reiniciando sozinho)", () => {
  it("reinicia sem duplicar texto já reconhecido", () => {
    let base = "";
    let sessao = "";

    sessao = mesclarResultadoDeSessao(sessao, "supino");
    sessao = mesclarResultadoDeSessao(sessao, "supino reto");
    sessao = mesclarResultadoDeSessao(sessao, "supino reto 3");
    sessao = mesclarResultadoDeSessao(sessao, "supino reto 3 10 repetições");
    expect(textoCompleto(base, sessao)).toBe("supino reto 3 10 repetições");

    // Android encerra a sessão sozinho: fecha a sessão atual na base e reabre vazia
    base = iniciarNovaSessao(base, sessao);
    sessao = "";
    expect(textoCompleto(base, sessao)).toBe("supino reto 3 10 repetições");

    // nova sessão continua a fala, sem repetir o que já foi reconhecido
    sessao = mesclarResultadoDeSessao(sessao, "com");
    sessao = mesclarResultadoDeSessao(sessao, "com oitenta");
    expect(textoCompleto(base, sessao)).toBe("supino reto 3 10 repetições com oitenta");
  });
});
