function entrarReino(reino){
 const erro=document.getElementById('erro-reino');
 erro.textContent='Entrando em '+reino+'...';
 window.RB.entrarVisitante(reino).catch(e=>{erro.textContent='❌ '+e.message;});
}
function abrirAdmin(){
 document.getElementById('login-admin').style.display='block';
 document.getElementById('erro-reino').textContent='';
 document.getElementById('email-admin').focus();
}
async function entrarAdmin(){
 const erro=document.getElementById('erro-senha');
 erro.textContent='Entrando...';
 try{await window.RB.entrar(document.getElementById('email-admin').value,document.getElementById('senha-admin').value,'Admin')}
 catch(e){erro.textContent='❌ '+e.message}
}
document.addEventListener('keydown',e=>{if(e.key==='Enter'&&document.getElementById('login-admin').style.display==='block')entrarAdmin()});
