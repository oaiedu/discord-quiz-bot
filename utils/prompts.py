def prompt_multiple_choice(topico, texto, qty):
    return f"""
    Você é um gerador de perguntas. Com base no conteúdo abaixo, gere {qty} perguntas de múltipla escolha.
    Cada pergunta deve conter quatro alternativas (A, B, C, D) e indicar a correta com a letra.
    Retorne em formato JSON como este:
    [
    {{
        "pergunta": "...",
        "alternativas": {{
            "A": "...",
            "B": "...",
            "C": "...",
            "D": "..."
        }},
        "resposta": "B"
    }},
    ...
    ]

    Tema: {topico}

    Conteúdo:
    {texto[:4000]}  # Limite para evitar excesso de tokens
    """

def prompt_true_false(topico, texto, qty):
    return f"""
    Você é um gerador de perguntas. Com base no conteúdo abaixo, gere {qty} perguntas de verdadeiro ou falso.
    Retorne em formato JSON como este:
    [
    {{
        "pergunta": "...",
        "resposta": "V"
    }},
    ...
    ]

    Tema: {topico}

    Conteúdo:
    {texto[:4000]}
    """

def prompt_short_answer(topico, texto, qty):
    return f"""
    Você é um gerador de perguntas. Com base no conteúdo abaixo, gere {qty} perguntas de resposta curta.
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
    Você é um gerador de perguntas. Com base no conteúdo abaixo, gere {qty} perguntas variadas.
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