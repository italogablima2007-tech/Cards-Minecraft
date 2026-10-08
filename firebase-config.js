import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js';
import { getAuth, onAuthStateChanged, signInWithEmailAndPassword, signInAnonymously, signOut } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js';
import { getFirestore, doc, getDoc, getDocs, collection, setDoc, deleteDoc, runTransaction, onSnapshot } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js';
const app = initializeApp({
  apiKey: 'AIzaSyCgR1FUw7gaQKTs0Tea0GAymsK97cHpBrM',
  authDomain: 'reinos-e-batalhas.firebaseapp.com',
  projectId: 'reinos-e-batalhas',
  storageBucket: 'reinos-e-batalhas.firebasestorage.app',
  messagingSenderId: '39778437620',
  appId: '1:39778437620:web:9e4c7690d42ccaa204d1a1',
  measurementId: 'G-7P807DPL45'
});
const auth=getAuth(app), db=getFirestore(app);
const ADMIN_UID='PnQ1N44V4ETTG6koXcW8JZpmh3P2';
const reinos=['Drakmor','Solaris','Aetheryon'];
const authReady=new Promise(resolve=>{const unsubscribe=onAuthStateChanged(auth,u=>{unsubscribe();resolve(u)})});
async function perfil(){await authReady;const u=auth.currentUser;if(!u)return null;if(u.isAnonymous){const reino=localStorage.getItem('reinoVisitante');return reinos.includes(reino)?{uid:u.uid,reino,admin:false,visitante:true}:null;}if(u.uid===ADMIN_UID)return {uid:u.uid,reino:'Admin',admin:true};const snap=await getDoc(doc(db,'usuarios',u.uid));const reino=snap.exists()?snap.data().reino:null;return reinos.includes(reino)?{uid:u.uid,reino,admin:false}:null}
async function exigir(){let x;try{x=await perfil()}catch(e){alert('Não foi possível verificar o login: '+e.message);location.replace('index.html');throw e}if(!x){location.replace('index.html');throw Error('Login ou reino não configurado')}localStorage.setItem('usuarioLogado',x.reino);return x}
async function entrarVisitante(reino){if(!reinos.includes(reino))throw Error('Reino inválido');await authReady;if(auth.currentUser&&!auth.currentUser.isAnonymous)await signOut(auth);if(!auth.currentUser)await signInAnonymously(auth);localStorage.setItem('reinoVisitante',reino);localStorage.setItem('usuarioLogado',reino);location.href='painel.html'}
async function entrar(email,senha,escolha){const cred=await signInWithEmailAndPassword(auth,email,senha);const x=await perfil();if(!x||x.reino!==escolha){await signOut(auth);throw Error('Esta conta não tem permissão para entrar como '+escolha+'.')}localStorage.setItem('usuarioLogado',x.reino);location.href='painel.html'}
async function sair(){await signOut(auth);localStorage.removeItem('reinoVisitante');localStorage.removeItem('usuarioLogado');localStorage.removeItem('reinoAdministrado');location.href='index.html'}
async function listarCartas(){const snap=await getDocs(collection(db,'cartas'));return snap.docs.map(d=>d.data()).sort((a,b)=>Number(a.id)-Number(b.id))}
async function salvarCarta(c){await setDoc(doc(db,'cartas',String(c.id)),c)}
async function apagarCarta(id){await deleteDoc(doc(db,'cartas',String(id)))}
async function inventario(reino){const s=await getDoc(doc(db,'inventarios',reino));return s.exists()?(s.data().cartas||[]):[]}
async function adicionarCartas(reino,ids){await runTransaction(db,async tx=>{const ref=doc(db,'inventarios',reino);const s=await tx.get(ref);const lista=s.exists()?[...(s.data().cartas||[])]:[];for(const id of ids){const it=lista.find(x=>String(x.idCarta)===String(id));if(it)it.quantidade=Number(it.quantidade||0)+1;else lista.push({idCarta:id,quantidade:1,nivel:1,xp:0})}tx.set(ref,{cartas:lista})})}
async function importarCartas(){const dados=JSON.parse(localStorage.getItem('cartasReinos')||'[]');if(!Array.isArray(dados)||!dados.length)throw Error('Nenhuma carta local encontrada neste navegador.');const atuais=await listarCartas();const existentes=new Set(atuais.map(x=>String(x.id)));let n=0;for(const c of dados){if(!existentes.has(String(c.id))){await salvarCarta(c);n++}}return n}
window.RB={auth,db,ADMIN_UID,authReady,perfil,exigir,entrar,entrarVisitante,sair,listarCartas,salvarCarta,apagarCarta,inventario,adicionarCartas,importarCartas,doc,getDoc,setDoc,onSnapshot};
