let reinoSelecionado=null;
function entrarReino(reino){
  reinoSelecionado=reino;
  document.getElementById('login-reino').style.display='block';
  document.getElementById('reino-escolhido').textContent='🔐 Código de '+reino;
  document.getElementById('codigo-reino').value='';
  document.getElementById('erro-reino').textContent='';
  document.getElementById('codigo-reino').focus();
}
async function confirmarReino(){
  const erro=document.getElementById('erro-reino');
  erro.textContent='Verificando código...';
  try{await window.RB.entrarReino(reinoSelecionado,document.getElementById('codigo-reino').value)}
  catch(e){erro.textContent='❌ Código inválido ou acesso indisponível. Confira e tente novamente.';}
}
function abrirAdmin(){
  document.getElementById('login-admin').style.display='block';
  document.getElementById('login-reino').style.display='none';
  document.getElementById('erro-reino').textContent='';
  document.getElementById('email-admin').focus();
}
async function entrarAdmin(){
  const erro=document.getElementById('erro-senha');
  erro.textContent='Entrando...';
  try{await window.RB.entrar(document.getElementById('email-admin').value,document.getElementById('senha-admin').value,'Admin')}
  catch(e){erro.textContent='❌ E-mail ou senha inválidos, ou acesso não autorizado.'}
}
document.addEventListener('keydown',e=>{if(e.key!=='Enter')return;if(document.activeElement?.id==='codigo-reino')confirmarReino();else if(document.getElementById('login-admin').style.display==='block')entrarAdmin()});
