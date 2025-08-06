def prompt_multiple_choice(topico, texto, qty):
    return f"""
Você é um gerador de perguntas. Gere **exatamente {qty}** perguntas de múltipla escolha com base no conteúdo abaixo, e **não gere nenhuma pergunta extra**.

Cada pergunta deve conter quatro alternativas (A, B, C, D), e apenas uma correta. A resposta correta deve ser indicada com a letra.

Formato da saída em JSON:
[
{{
    "pergunta": "Texto da pergunta...",
    "alternativas": {{
        "A": "Alternativa A",
        "B": "Alternativa B",
        "C": "Alternativa C",
        "D": "Alternativa D"
    }},
    "resposta": "B"
}},
...
]  # Exatamente {qty} objetos como esse

Tema: {topico}

Conteúdo:
{texto[:4000]}
"""

def prompt_true_false(topico, texto, qty):
    return f"""
Você é um gerador de perguntas. Gere **exatamente {qty}** perguntas de verdadeiro ou falso com base no conteúdo abaixo, e **não gere nenhuma pergunta extra**.

Formato da saída em JSON:
[
{{
    "pergunta": "Texto da pergunta...",
    "resposta": "Verdadeiro"  # ou "Falso"
}},
...
]  # Exatamente {qty} objetos como esse

Tema: {topico}

Conteúdo:
{texto[:4000]}
"""

def prompt_short_answer(topico, texto, qty):
    return f"""
    Você é um gerador de perguntas. Com base no conteúdo abaixo, gere {qty} perguntas de resposta curta, e não gere nenhuma extra. Somente {qty}.
    Retorne em formato JSON como este:
    [
    {{
        "pergunta": "...",
        "resposta": "..."
    }},
    ...
    ]

    Tema: {topico}

    Conteúdo:
    {texto[:4000]}
    """

def prompt_default(topico, texto, qty):
    return f"""
    Você é um gerador de perguntas. Com base no conteúdo abaixo, gere {qty} perguntas variadas, e não gere nenhuma extra. Somente {qty}.
    Retorne em formato JSON como este:
    [
    {{
        "pergunta": "...",
        "resposta": "..."
    }},
    ...
    ]

    Tema: {topico}

    Conteúdo:
    {texto[:4000]}
    """