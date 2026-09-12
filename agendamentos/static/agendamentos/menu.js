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

    function mostrarPagina(pagina) {
        menuInicial.classList.add("escondida");
        aplicativo.classList.remove("escondida");

        itensMenu.forEach(function (item) {
            item.classList.remove("ativo");
            if (item.getAttribute("data-pagina") === pagina) {
                item.classList.add("ativo");
            }
        });

        conteudoAgenda.style.display = "block";
        conteudoEmBreve.style.display = "none";

        if (pagina !== "agenda") {
            conteudoAgenda.style.display = "none";
            conteudoEmBreve.style.display = "block";
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

    btnMenu.addEventListener("click", function () {
        menuNavegacao.classList.toggle("aberto");
    });

    btnMenuInicial.addEventListener("click", function () {
        aplicativo.classList.add("escondida");
        menuInicial.classList.remove("escondida");
        menuNavegacao.classList.remove("aberto");
        itensMenu.forEach(function (item) {
            item.classList.remove("ativo");
        });
    });

});