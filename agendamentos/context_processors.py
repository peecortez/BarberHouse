def tipo_usuario(request):
    """Disponibiliza em todos os templates:

    - `tipo_usuario`: 'cliente', 'profissional' ou None (usado pela barra de navegacao);
    - `primeiro_nome`: primeiro nome do perfil logado, ou '' (usado na saudacao da home).
    """
    usuario = getattr(request, "user", None)
    if not usuario or not usuario.is_authenticated:
        return {"tipo_usuario": None, "primeiro_nome": ""}

    perfil, tipo = None, None
    if hasattr(usuario, "profissional"):
        perfil, tipo = usuario.profissional, "profissional"
    elif hasattr(usuario, "cliente"):
        perfil, tipo = usuario.cliente, "cliente"

    nome = (getattr(perfil, "nome", "") or "").strip()
    return {"tipo_usuario": tipo, "primeiro_nome": nome.split()[0] if nome else ""}
