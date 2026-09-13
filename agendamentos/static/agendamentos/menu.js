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
});
