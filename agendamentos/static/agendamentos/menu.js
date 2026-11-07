
function abrirDialogo(mensagem, opcoes = {}) {
    return new Promise(resolve => {
        const dialog = document.createElement("dialog");
        dialog.className = "confirmacao-dialog";
        dialog.setAttribute("aria-labelledby", "tituloConfirmacao");
        dialog.setAttribute("aria-describedby", "mensagemConfirmacao");

        const titulo = document.createElement("h2");
        titulo.id = "tituloConfirmacao";
        titulo.textContent = opcoes.titulo || "Estamos quase lá";

        const texto = document.createElement("p");
        texto.id = "mensagemConfirmacao";
        texto.textContent = mensagem;

        let caixa = null;
        let rotulo = null;
        if (opcoes.rotuloCheckbox) {
            rotulo = document.createElement("label");
            rotulo.className = "confirmacao-opcao";
            caixa = document.createElement("input");
            caixa.type = "checkbox";
            rotulo.append(caixa, document.createTextNode(" " + opcoes.rotuloCheckbox));
        }

        const botoes = document.createElement("div");
        botoes.className = "confirmacao-acoes";

        const voltar = document.createElement("button");
        voltar.type = "button";
        voltar.className = "botao-secundario";
        voltar.textContent = "Voltar";
        voltar.addEventListener("click", () => dialog.close("cancel"));

        const confirmar = document.createElement("button");
        confirmar.type = "button";
        confirmar.className = "botao-principal";
        confirmar.textContent = opcoes.textoConfirmar || "Confirmar";
        confirmar.addEventListener("click", () => dialog.close("confirm"));

        botoes.append(voltar, confirmar);
        dialog.append(titulo, texto);
        if (rotulo) dialog.append(rotulo);
        dialog.append(botoes);
        dialog.addEventListener("cancel", event => {
            event.preventDefault();
            dialog.close("cancel");
        });
        dialog.addEventListener("close", () => {
            const aceito = dialog.returnValue === "confirm";
            const marcado = caixa ? caixa.checked : false;
            dialog.remove();
            resolve({ aceito, marcado });
        });

        document.body.appendChild(dialog);
        dialog.showModal();
        voltar.focus();
    });
}

function confirmarAcao(mensagem) {
    return abrirDialogo(mensagem).then(resultado => resultado.aceito);
}

// Le um cookie pelo nome (usado para enviar o token CSRF nas requisicoes)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// SVGs do logo (.svg-animado) usam animacao SMIL, que o CSS de "reduzir
// movimento" nao alcanca: para essas pessoas, congela o bigode na posicao de repouso.
const reduzirMovimento = window.matchMedia('(prefers-reduced-motion: reduce)');

function ajustarSvgsAnimados() {
    document.querySelectorAll('svg.svg-animado').forEach(svg => {
        if (typeof svg.pauseAnimations !== 'function') return;
        if (reduzirMovimento.matches) {
            svg.pauseAnimations();
            svg.setCurrentTime(0);
        } else {
            svg.unpauseAnimations();
        }
    });
}

document.addEventListener('DOMContentLoaded', ajustarSvgsAnimados);
reduzirMovimento.addEventListener('change', ajustarSvgsAnimados);

// Transicao entre paginas (View Transitions, ver barbearia.css).
// Quando a pagina chega por transicao, marca o <html> para o cabecalho
// nao repetir a animacao de entrada (ele ja vem do morph).
window.addEventListener('pagereveal', function (event) {
    if (event.viewTransition) {
        document.documentElement.classList.add('vt-chegada');
    }
});

// Home: o card clicado vira o cabecalho da proxima pagina. O nome da
// transicao sai do cabecalho da home e vai para o card (nomes sao unicos).
function limparTransicaoCards() {
    document.querySelectorAll('.opcao-menu-inicial').forEach(card => {
        card.style.viewTransitionName = '';
    });
    const cabecalho = document.querySelector('.pagina-cabecalho');
    if (cabecalho) cabecalho.style.viewTransitionName = '';
}

document.addEventListener('click', function (event) {
    const card = event.target.closest('.opcao-menu-inicial');
    // Ctrl/Cmd/Shift-clique abre outra aba: nada de transicao nesta
    if (!card || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    limparTransicaoCards();
    const cabecalho = document.querySelector('.pagina-cabecalho');
    if (cabecalho) cabecalho.style.viewTransitionName = 'none';
    card.style.viewTransitionName = 'cabecalho-pagina';
});

// Voltando para a home pelo botao "voltar" (cache do navegador), desfaz os nomes
window.addEventListener('pageshow', function (event) {
    if (event.persisted) limparTransicaoCards();
});

document.addEventListener('DOMContentLoaded', function () {

    // Barra de navegacao (base_app.html): abre/fecha os links no celular
    const btnAlternarNav = document.querySelector('.nav-app-alternar');
    const navApp = document.querySelector('.nav-app');
    // Ao rolar a pagina, a barra deixa de ser transparente e ganha fundo com blur
    if (navApp) {
        const atualizarNav = () => navApp.classList.toggle('rolado', window.scrollY > 8);
        atualizarNav();
        window.addEventListener('scroll', atualizarNav, { passive: true });
    }

    if (btnAlternarNav && navApp) {
        btnAlternarNav.addEventListener('click', function () {
            const aberto = navApp.classList.toggle('aberto');
            btnAlternarNav.setAttribute('aria-expanded', String(aberto));
            btnAlternarNav.setAttribute('aria-label', aberto ? 'Fechar menu' : 'Abrir menu');
        });
    }

    // Botao de mostrar/ocultar senha (login)
    document.querySelectorAll('[data-alternar-senha]').forEach(function (botao) {
        const campo = document.getElementById(botao.dataset.alternarSenha);
        const icone = botao.querySelector('i');
        if (!campo) return;
        botao.addEventListener('click', function () {
            const mostrar = campo.type === 'password';
            campo.type = mostrar ? 'text' : 'password';
            botao.setAttribute('aria-label', mostrar ? 'Ocultar senha' : 'Mostrar senha');
            botao.setAttribute('aria-pressed', String(mostrar));
            if (icone) {
                icone.classList.toggle('fa-eye', !mostrar);
                icone.classList.toggle('fa-eye-slash', mostrar);
            }
        });
    });

    // Cadastro: mascara de CPF e conferencia da confirmacao de senha
    const formCadastro = document.getElementById('formCadastro');
    if (formCadastro) {
        const campoSenha = document.getElementById('senha');
        const campoConfirmacao = document.getElementById('senha_confirmacao');
        const feedbackSenha = document.getElementById('senhaFeedback');
        const campoCpf = document.getElementById('cpf');

        function validarConfirmacao(mostrarIncompleta = false) {
            const senha = campoSenha.value;
            const confirmacao = campoConfirmacao.value;
            const divergente = confirmacao && (
                !senha.startsWith(confirmacao) ||
                (mostrarIncompleta && senha !== confirmacao)
            );

            campoConfirmacao.setAttribute('aria-invalid', divergente ? 'true' : 'false');
            feedbackSenha.className = 'feedback-senha';

            if (divergente) {
                feedbackSenha.textContent = 'As senhas não coincidem.';
                feedbackSenha.classList.add('erro');
                return false;
            }

            if (confirmacao && senha === confirmacao) {
                feedbackSenha.textContent = 'As senhas coincidem.';
                feedbackSenha.classList.add('ok');
                return true;
            }

            feedbackSenha.textContent = '';
            return !mostrarIncompleta;
        }

        if (campoCpf) {
            campoCpf.addEventListener('input', function () {
                const d = this.value.replace(/\D/g, '').slice(0, 11);
                this.value = d
                    .replace(/^(\d{3})(\d)/, '$1.$2')
                    .replace(/^(\d{3})\.(\d{3})(\d)/, '$1.$2.$3')
                    .replace(/\.(\d{3})(\d)/, '.$1-$2');
            });
        }

        campoSenha.addEventListener('input', () => validarConfirmacao());
        campoConfirmacao.addEventListener('input', () => validarConfirmacao());

        // Registrado antes do listener do overlay: se bloquear o envio,
        // o overlay ve o defaultPrevented e nao aparece.
        formCadastro.addEventListener('submit', function (event) {
            if (!validarConfirmacao(true)) {
                event.preventDefault();
                campoConfirmacao.focus();
            }
        });
    }

    // Overlay "carregando" ao enviar formularios marcados com data-carregando
    const overlayCarregando = document.getElementById('overlayCarregando');
    if (overlayCarregando) {
        document.querySelectorAll('form[data-carregando]').forEach(function (form) {
            form.addEventListener('submit', function (event) {
                if (event.defaultPrevented) return;
                overlayCarregando.hidden = false;
            });
        });
    }

    // Noticias: revelar e copiar o cupom
    const botaoCupom = document.getElementById('botaoCupom');
    if (botaoCupom) {
        const areaCupom = document.getElementById('areaCupom');
        const botaoCopiar = document.getElementById('botaoCopiar');

        botaoCupom.addEventListener('click', () => {
            areaCupom.classList.remove('escondida');
            areaCupom.classList.add('cupom-revelado');
            botaoCupom.classList.add('escondida');
            botaoCupom.setAttribute('aria-expanded', 'true');
        });

        botaoCopiar.addEventListener('click', async () => {
            const rotulo = botaoCopiar.querySelector('span');
            try {
                await navigator.clipboard.writeText(document.getElementById('codigoCupom').textContent.trim());
                rotulo.textContent = 'Código copiado!';
            } catch (e) {
                rotulo.textContent = 'Selecione e copie o código acima';
            }
            setTimeout(() => { rotulo.textContent = 'Copiar código'; }, 2500);
        });
    }

    // Agendamento: confirmacao antes de enviar e carregamento dos horarios livres
    const formEl = document.getElementById('formAgendamento');
    if (formEl) {
        let agendamentoConfirmado = false;
        formEl.addEventListener('submit', async function (event) {
            if (agendamentoConfirmado) {
                agendamentoConfirmado = false;
                return;
            }

            event.preventDefault();
            const aceito = await confirmarAcao('Deseja confirmar este agendamento?');
            if (aceito) {
                agendamentoConfirmado = true;
                formEl.requestSubmit();
            }
        });

        const baseUrl = formEl.dataset.horariosUrl;

        const servicoSelect = document.getElementById('servico');
        const profissionalSelect = document.getElementById('profissional');
        const dataInput = document.getElementById('data');
        const horarioSelect = document.getElementById('horario');
        const opcaoVazia = '<option value="">Selecione um horário</option>';

        function loadHorarios() {
            const servicoId = servicoSelect?.value ?? '';
            const profissionalId = profissionalSelect?.value ?? '';
            const data = dataInput?.value ?? '';

            if (!servicoId || !profissionalId || !data) {
                if (horarioSelect) horarioSelect.innerHTML = opcaoVazia;
                return;
            }

            const url = `${baseUrl}?servico=${servicoId}&profissional=${profissionalId}&data=${data}`;

            fetch(url)
                .then(response => response.text().then(text => ({ ok: response.ok, text })))
                .then(({ ok, text }) => {
                    if (!horarioSelect) return;
                    if (!ok) {
                        horarioSelect.innerHTML = opcaoVazia;
                        return;
                    }
                    let dataJson;
                    try {
                        dataJson = JSON.parse(text);
                    } catch (e) {
                        horarioSelect.innerHTML = opcaoVazia;
                        return;
                    }
                    if (Array.isArray(dataJson.horarios)) {
                        horarioSelect.innerHTML = opcaoVazia +
                            dataJson.horarios.map(hora => `<option value="${hora}">${hora}</option>`).join('');
                    } else {
                        horarioSelect.innerHTML = opcaoVazia;
                    }
                })
                .catch(() => {
                    if (horarioSelect) horarioSelect.innerHTML = opcaoVazia;
                });
        }

        if (servicoSelect) servicoSelect.addEventListener('change', loadHorarios);
        if (profissionalSelect) profissionalSelect.addEventListener('change', loadHorarios);
        if (dataInput) dataInput.addEventListener('change', loadHorarios);
    }

    // Profissional: abrir/fechar a agenda
    const btnToggleAgenda = document.getElementById("btnToggleAgenda");
    if (btnToggleAgenda) {
        btnToggleAgenda.addEventListener("click", function () {
            btnToggleAgenda.disabled = true;
            fetch("/toggle-agenda-aberta/", {
                method: "POST",
                headers: { "X-CSRFToken": getCookie("csrftoken") }
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        window.location.reload();
                    } else {
                        showMessage(data.error || "Erro ao atualizar a agenda", "error");
                        btnToggleAgenda.disabled = false;
                    }
                })
                .catch(() => {
                    showMessage("Erro ao atualizar a agenda", "error");
                    btnToggleAgenda.disabled = false;
                });
        });
    }

    // Botoes de status dos agendamentos (confirmar / concluir / cancelar)
    document.addEventListener('click', async function(e) {
        const button = e.target.closest('button[data-acao][data-id]');
        if (!button) return;

        const acao = button.getAttribute('data-acao');
        const id = button.getAttribute('data-id');

        if (acao === 'cancelar') {
            const aceito = await confirmarAcao('Deseja cancelar este agendamento?');
            if (!aceito) return;
        }

        let cupom = false;
        if (acao === 'concluir') {
            const opcoes = {
                titulo: 'Concluir atendimento',
                textoConfirmar: 'Concluir',
            };
            if (button.hasAttribute('data-cupom-disponivel')) {
                opcoes.rotuloCheckbox = 'O cliente aplicou o cupom de 15% de desconto';
            }
            const resultado = await abrirDialogo('Confirmar que este atendimento foi concluído?', opcoes);
            if (!resultado.aceito) return;
            cupom = resultado.marcado;
        }

        // Evita clique duplo enquanto a requisicao esta em andamento
        button.disabled = true;

        fetch(`/agendamento/${id}/status/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({ acao: acao, cupom: cupom })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
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

// Toasts (_toasts.html): o tempo na tela e a barra de progresso do CSS (6s).
// Quando ela termina, o toast sai; mouse ou foco em cima pausam a barra.
// O "x" fecha na hora.
function fecharToast(toast) {
    if (toast.classList.contains('saindo')) return;
    toast.classList.add('saindo');
    toast.addEventListener('animationend', function (event) {
        if (event.target === toast) toast.remove();
    });
}

document.querySelectorAll('.toast').forEach(function (toast) {
    const progresso = toast.querySelector('.toast-progresso');
    if (progresso) {
        progresso.addEventListener('animationend', function () {
            fecharToast(toast);
        }, { once: true });
    }

    const fechar = toast.querySelector('.toast-fechar');
    if (fechar) {
        fechar.addEventListener('click', function () {
            fecharToast(toast);
        });
    }
});

// Mostra uma mensagem temporaria logo abaixo do cabecalho da pagina
function showMessage(message, type) {
    document.querySelectorAll('.mensagem').forEach(el => el.remove());

    const messageEl = document.createElement('div');
    messageEl.className = `mensagem ${type}`;
    messageEl.setAttribute('role', 'alert');
    messageEl.textContent = message;

    const ancora = document.querySelector('.pagina-cabecalho') || document.querySelector('.caixa-login .subtitulo');
    if (ancora) {
        ancora.after(messageEl);
    } else {
        document.body.prepend(messageEl);
    }

    setTimeout(() => {
        messageEl.remove();
    }, 5000);
}
