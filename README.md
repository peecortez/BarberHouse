# BarberHouse

Sistema web para gerenciamento de uma barbearia, desenvolvido com Django. Clientes podem consultar serviços e profissionais com agenda aberta, verificar horários disponíveis e acompanhar seus agendamentos. Profissionais podem gerenciar a própria agenda e atualizar o status dos atendimentos.

## Funcionalidades

- Cadastro e login de clientes e profissionais, com CPF validado (dígitos verificadores e unicidade), previsto para validação de cupons e promoções.
- Cadastro de serviços pelo painel administrativo do Django.
- Consulta de horários disponíveis por serviço, profissional e data.
- Criação e acompanhamento de agendamentos.
- Notificação no canto superior direito confirmando o agendamento, exibida por 7 segundos.
- Visualização separada de agendamentos ativos, concluídos e cancelados.
- Identificação de quem cancelou cada agendamento.
- Confirmação, conclusão e cancelamento de atendimentos, conforme o perfil do usuário.
- Abertura e fechamento da agenda do profissional.
- Notícia de promoção com código de 15% de desconto (`BARBER15OFF` + 3 últimos dígitos do CPF), um por CPF, exibido ao cliente logado. O profissional valida o uso ao concluir o atendimento; depois disso o cliente vê "Cupom já resgatado".
- Painel administrativo para gerenciar os dados do sistema.

## Tecnologias

- Python
- Django
- SQLite
- HTML, CSS e JavaScript

## Requisitos

- Python instalado.
- `pip` disponível no ambiente.

> As dependencias estao listadas em requirements.txt.

## Como executar localmente

No terminal, entre na pasta do projeto:

```bash
cd BarberHouse
```

Crie e ative um ambiente virtual (opcional, mas recomendado):

```bash
python -m venv venv
```

No Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

No macOS ou Linux:

```bash
source venv/bin/activate
```

Instale o Django:

```bash
python -m pip install -r requirements.txt
```

Aplique as migrações e inicie o servidor:

```bash
python manage.py migrate
python manage.py runserver
```

Abra <http://127.0.0.1:8000/> no navegador. O painel administrativo fica em <http://127.0.0.1:8000/admin/>.

Para criar um usuário administrador:

```bash
python manage.py createsuperuser
```

Cadastre serviços pelo painel administrativo antes de realizar agendamentos.

## Fluxo de uso

1. Crie uma conta como cliente ou profissional pela página de cadastro.
2. Entre com o e-mail e a senha cadastrados.
3. Como profissional, cadastre ou solicite que um administrador cadastre serviços e gerencie os agendamentos recebidos. A agenda começa aberta e pode ser fechada na interface.
4. Como cliente, escolha um serviço, um profissional disponível, uma data e um horário para agendar.
5. Acompanhe ou cancele seus agendamentos na área correspondente.

Os horários são oferecidos em intervalos de 30 minutos entre 8h e 18h, considerando a duração do serviço e os agendamentos existentes.

## Estrutura do projeto

```text
BarberHouse/
├── agendamentos/       # Modelos, telas, formulários, rotas e arquivos estáticos
├── barbearia/          # Configurações e rotas principais do Django
├── manage.py           # Utilitário de administração do Django
└── db.sqlite3          # Banco SQLite local (criado/atualizado pelas migrações)
```

## Observações

As configuracoes padrao sao para desenvolvimento local. Antes de publicar, defina DJANGO_SECRET_KEY, DJANGO_DEBUG=False e DJANGO_ALLOWED_HOSTS no ambiente, alem de configurar HTTPS e um banco de producao.
