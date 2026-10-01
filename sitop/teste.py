import requests


def consultar_sitop(usuario, senha):

    # =========================
    # LOGIN
    # =========================

    login_url = "https://csdpocos.petrobras.com.br/api/login"

    login_data = {
        "user": usuario,
        "password": senha
    }

    login_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    login = requests.post(
        login_url,
        json=login_data,
        headers=login_headers,
        timeout=30
    )

    print("HTTP Login:", login.status_code)

    login.raise_for_status()

    login_json = login.json()

    token = login_json.get("token")

    if not token:
        raise Exception("Token não encontrado na resposta do login.")

    print("Token obtido com sucesso.")

    # =========================
    # CONSULTA SITOP
    # =========================

    sitop_url = (
        "https://csdpocos.petrobras.com.br/"
        "holistico/api/octopus/sitop/"
    )

    sitop_headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "App": "holistico"
    }

    response = requests.get(
        sitop_url,
        headers=sitop_headers,
        timeout=30
    )

    print("HTTP SITOP:", response.status_code)

    response.raise_for_status()

    return response.json()


# Exemplo
usuario = "meu_usuario"
senha = "minha_senha"

try:
    resultado = consultar_sitop(usuario, senha)

    print(resultado)

except requests.RequestException as erro:
    print("Erro HTTP:", erro)

except Exception as erro:
    print("Erro:", erro)