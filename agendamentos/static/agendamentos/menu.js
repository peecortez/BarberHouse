// Helper function to get cookie value by name
// FIXED: Added getCookie for CSRF token in status update buttons
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.addEventListener('DOMContentLoaded', function () {

    const aplicativo = document.getElementById("aplicativo");
    const menuInicial = document.getElementById("menuInicial");
    const btnMenu = document.getElementById("btnMenu");
    const menuNavegacao = document.getElementById("menuNavegacao");
    const btnMenuInicial = document.getElementById("btnMenuInicial");
    const itensMenu = document.querySelectorAll(".item-menu[data-pagina]");
    const conteudoAgenda = document.getElementById("conteudoAgenda");
    const conteudoEmBreve = document.getElementById("conteudoEmBreve");
    const opcoesMenuInicial = document.querySelectorAll(".opcao-menu-inicial");
    const loadingGlobal = document.querySelector(".loading");

    function mostrarPagina(pagina) {
        const rotas = { agenda: "/agenda-cliente/", atendimento: "/meus-agendamentos/", noticias: "/noticias/", mais: "/mais/", "minha-agenda": "/gerenciar-agenda/" };
        if (rotas[pagina]) { window.location.href = rotas[pagina]; return; }
        menuInicial.classList.add("escondida");
        aplicativo.classList.remove("escondida");

        itensMenu.forEach(function (item) {
            item.classList.remove("ativo");
            if (item.getAttribute("data-pagina") === pagina) {
                item.classList.add("ativo");
            }
        });

        conteudoAgenda.style.removeProperty("display");
        conteudoEmBreve.style.removeProperty("display");


        if (pagina === "agenda") {
            conteudoAgenda.classList.remove("escondida");
            conteudoEmBreve.classList.add("escondida");

            conteudoAgenda.style.setProperty("display", "flex", "important");
            conteudoEmBreve.style.setProperty("display", "none", "important");
        } else {
            conteudoAgenda.classList.add("escondida");
            conteudoEmBreve.classList.remove("escondida");

            conteudoAgenda.style.setProperty("display", "none", "important");
            conteudoEmBreve.style.setProperty("display", "flex", "important");
        }

        if (loadingGlobal) {
            loadingGlobal.classList.add("escondida");
            loadingGlobal.style.setProperty("display", "none", "important");
        }
    }

    opcoesMenuInicial.forEach(function (opcao) {
        opcao.addEventListener("click", function () {
            mostrarPagina(opcao.getAttribute("data-pagina"));
        });
    });

    itensMenu.forEach(function (item) {
        item.addEventListener("click", function () {
            mostrarPagina(item.getAttribute("data-pagina"));
            menuNavegacao.classList.remove("aberto");
        });
    });

    if (btnMenu) {
        btnMenu.addEventListener("click", function () {
            menuNavegacao.classList.toggle("aberto");
        });
    }

    if (btnMenuInicial) {
        btnMenuInicial.addEventListener("click", function () {
            aplicativo.classList.add("escondida");
            menuInicial.classList.remove("escondida");
            menuNavegacao.classList.remove("aberto");
            itensMenu.forEach(function (item) {
                item.classList.remove("ativo");
            });
        });
    }

    // Handle status change buttons
    document.addEventListener('click', function(e) {
        const button = e.target.closest('button[data-acao][data-id]');
        if (!button) return;

        const acao = button.getAttribute('data-acao');
        const id = button.getAttribute('data-id');

        // Disable button to prevent double clicks
        button.disabled = true;

        fetch(`/agendamento/${id}/status/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ acao: acao })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload the page to reflect the new status
                window.location.reload();
            } else {
                showMessage(data.error || 'Erro desconhecido', 'error');
                button.disabled = false;
            }
        })
        .catch(error => {
            console.error('Error updating status:', error);
            showMessage('Erro ao atualizar status', 'error');
            button.disabled = false;
        });
    });

});
