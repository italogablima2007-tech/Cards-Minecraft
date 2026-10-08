// ==========================================
// REINOS & BATALHAS
// SISTEMA DE LOGIN
// ==========================================


// ==========================================
// LOGIN DOS REINOS
// ==========================================

function entrarReino(reino) {

    // Salva qual Reino entrou
    localStorage.setItem("usuarioLogado", reino);

    // Envia para o painel
    window.location.href = "painel.html";

}


// ==========================================
// ABRIR ÁREA DE LOGIN DO ADMIN
// ==========================================

function abrirAdmin() {

    const loginAdmin = document.getElementById("login-admin");

    // Mostra a caixa de senha
    loginAdmin.style.display = "block";

    // Limpa mensagens antigas
    document.getElementById("erro-senha").textContent = "";

    // Coloca o cursor automaticamente no campo
    document.getElementById("senha-admin").focus();

}


// ==========================================
// LOGIN DO ADMIN
// ==========================================

function entrarAdmin() {

    const senha = document.getElementById("senha-admin").value;

    const erro = document.getElementById("erro-senha");


    // Verifica a senha
    if (senha === "1822") {

        // Salva que o Admin entrou
        localStorage.setItem("usuarioLogado", "Admin");

        // Limpa mensagem de erro
        erro.textContent = "";

        // Envia para o painel
        window.location.href = "painel.html";

    } else {

        // Mostra erro
        erro.textContent = "❌ Senha incorreta.";

        // Limpa o campo
        document.getElementById("senha-admin").value = "";

        // Volta o cursor para o campo
        document.getElementById("senha-admin").focus();

    }

}


// ==========================================
// USAR ENTER PARA ENTRAR COMO ADMIN
// ==========================================

const campoSenha = document.getElementById("senha-admin");

if (campoSenha) {

    campoSenha.addEventListener("keydown", function(event) {

        if (event.key === "Enter") {

            entrarAdmin();

        }

    });

}