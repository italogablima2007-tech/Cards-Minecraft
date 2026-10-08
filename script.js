
let reinoSelecionado = null;

function entrarReino(reino) {
  reinoSelecionado = reino;

  document.getElementById('login-reino').style.display = 'block';
  document.getElementById('reino-escolhido').textContent = '🔐 Código de ' + reino;
  document.getElementById('codigo-reino').value = '';
  document.getElementById('erro-reino').textContent = '';
  document.getElementById('codigo-reino').focus();
}

async function confirmarReino() {
  const erro = document.getElementById('erro-reino');
  const codigo = document.getElementById('codigo-reino').value;

  erro.textContent = 'Verificando código...';

  try {
    if (!window.RB) {
      throw new Error('Firebase ainda não carregou');
    }

    await window.RB.entrarReino(reinoSelecionado, codigo);

  } catch (e) {
    console.error('Erro ao entrar no reino:', e.code || e.message);

    const mensagens = {
      'auth/invalid-credential': 'E-mail ou senha não reconhecidos pelo Firebase.',
      'auth/wrong-password': 'Senha incorreta.',
      'auth/user-not-found': 'Conta não encontrada.',
      'auth/too-many-requests': 'Muitas tentativas. Aguarde antes de tentar novamente.',
      'auth/network-request-failed': 'Falha na conexão com o Firebase.',
      'auth/operation-not-allowed': 'Login por e-mail e senha não está habilitado.',
      'auth/invalid-api-key': 'Configuração do Firebase inválida.'
    };

    erro.textContent = '❌ ' + (mensagens[e.code] || e.message || 'Erro desconhecido');
  }
}

function abrirAdmin() {
  document.getElementById('login-admin').style.display = 'block';
  document.getElementById('login-reino').style.display = 'none';
  document.getElementById('erro-reino').textContent = '';
  document.getElementById('email-admin').focus();
}

async function entrarAdmin() {
  const erro = document.getElementById('erro-senha');
  erro.textContent = 'Entrando...';

  try {
    await window.RB.entrar(
      document.getElementById('email-admin').value,
      document.getElementById('senha-admin').value,
      'Admin'
    );
  } catch (e) {
    console.error('Erro no login Admin:', e.code || e.message);
    erro.textContent = '❌ Não foi possível entrar. Confira os dados.';
  }
}

document.addEventListener('keydown', e => {
  if (e.key !== 'Enter') return;

  if (document.activeElement?.id === 'codigo-reino') {
    confirmarReino();
  } else if (document.getElementById('login-admin').style.display === 'block') {
    entrarAdmin();
  }
});
