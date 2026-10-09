
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js';
import { getAuth, onAuthStateChanged, signInWithEmailAndPassword, signOut } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js';
import { getFirestore, doc, getDoc, getDocs, collection, setDoc, deleteDoc, runTransaction, onSnapshot, addDoc, query, where, serverTimestamp } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js';

const app = initializeApp({
  apiKey: 'AIzaSyCgR1FUw7gaQKTs0Tea0GAymsK97cHpBrM',
  authDomain: 'reinos-e-batalhas.firebaseapp.com',
  projectId: 'reinos-e-batalhas',
  storageBucket: 'reinos-e-batalhas.firebasestorage.app',
  messagingSenderId: '39778437620',
  appId: '1:39778437620:web:9e4c7690d42ccaa204d1a1',
  measurementId: 'G-7P807DPL45'
});

const auth = getAuth(app);
const db = getFirestore(app);
const ADMIN_UID = 'PnQ1N44V4ETTG6koXcW8JZpmh3P2';

const reinos = ['Drakmor', 'Solaris', 'Aetheryon'];

const authReady = new Promise(resolve => {
  const unsubscribe = onAuthStateChanged(auth, u => {
    unsubscribe();
    resolve(u);
  });
});

const CONTAS_REINO = {
  Drakmor: {
    email: 'italopaodeforma@gmail.com',
    uid: 'o4TMyQzGeqT5XEclTRK5rA8tDOF2'
  },
  Solaris: {
    email: 'maycomventurim@gmail.com',
    uid: 'uwdUM1mMYEcMBKhC6XpNLrszAeI2'
  },
  Aetheryon: {
    email: 'lavinya.sloiola@gmail.com',
    uid: 'GMJajxBKyoZkJGDKfCcHzLmwrGl2'
  }
};

async function perfil() {
  await authReady;

  const u = auth.currentUser;
  if (!u) return null;

  if (u.uid === ADMIN_UID) {
    return { uid: u.uid, reino: 'Admin', admin: true };
  }

  const reino = Object.keys(CONTAS_REINO).find(
    r => CONTAS_REINO[r].uid === u.uid
  );

  return reino
    ? { uid: u.uid, reino, admin: false }
    : null;
}

async function exigir() {
  let x;

  try {
    x = await perfil();
  } catch (e) {
    alert('Não foi possível verificar o login: ' + e.message);
    location.replace('index.html');
    throw e;
  }

  if (!x) {
    location.replace('index.html');
    throw Error('Login não autorizado');
  }

  localStorage.setItem('usuarioLogado', x.reino);
  return x;
}

async function entrarReino(reino, codigo) {
  if (!CONTAS_REINO[reino]) throw Error('Reino inválido');
  if (!codigo) throw Error('Digite o código secreto');

  await authReady;

  const cred = await signInWithEmailAndPassword(
    auth,
    CONTAS_REINO[reino].email,
    codigo
  );

  if (cred.user.uid !== CONTAS_REINO[reino].uid) {
    await signOut(auth);
    throw Error('Esta conta não corresponde ao reino escolhido');
  }

  localStorage.setItem('usuarioLogado', reino);
  localStorage.removeItem('reinoVisitante');
  location.href = 'painel.html';
}

async function entrar(email, senha, escolha) {
  await authReady;

  const cred = await signInWithEmailAndPassword(
    auth,
    email,
    senha
  );

  if (escolha !== 'Admin' || cred.user.uid !== ADMIN_UID) {
    await signOut(auth);
    throw Error('Esta conta não tem permissão de administrador');
  }

  localStorage.setItem('usuarioLogado', 'Admin');
  location.href = 'painel.html';
}

async function sair() {
  await signOut(auth);

  localStorage.removeItem('reinoVisitante');
  localStorage.removeItem('usuarioLogado');
  localStorage.removeItem('reinoAdministrado');

  location.href = 'index.html';
}

// ==================================================
// CARTAS
// ==================================================

async function listarCartas() {
  const snap = await getDocs(collection(db, 'cartas'));

  return snap.docs
    .map(d => d.data())
    .sort((a, b) => Number(a.id) - Number(b.id));
}

async function salvarCarta(c) {
  await setDoc(doc(db, 'cartas', String(c.id)), c);
}

async function apagarCarta(id) {
  await deleteDoc(doc(db, 'cartas', String(id)));
}

// ==================================================
// INVENTÁRIO
// ==================================================

async function inventario(reino) {
  const s = await getDoc(doc(db, 'inventarios', reino));

  return s.exists()
    ? (s.data().cartas || [])
    : [];
}

async function adicionarCartas(reino, ids) {
  await runTransaction(db, async tx => {
    const ref = doc(db, 'inventarios', reino);
    const s = await tx.get(ref);

    const lista = s.exists()
      ? [...(s.data().cartas || [])]
      : [];

    for (const id of ids) {
      const it = lista.find(
        x => String(x.idCarta) === String(id)
      );

      if (it) {
        it.quantidade = Number(it.quantidade || 0) + 1;
      } else {
        lista.push({
          idCarta: id,
          quantidade: 1,
          nivel: 1,
          xp: 0
        });
      }
    }

    tx.set(ref, { cartas: lista });
  });
}

async function importarCartas() {
  const dados = JSON.parse(
    localStorage.getItem('cartasReinos') || '[]'
  );

  if (!Array.isArray(dados) || !dados.length) {
    throw Error('Nenhuma carta local encontrada neste navegador.');
  }

  const atuais = await listarCartas();
  const existentes = new Set(atuais.map(x => String(x.id)));

  let n = 0;

  for (const c of dados) {
    if (!existentes.has(String(c.id))) {
      await salvarCarta(c);
      n++;
    }
  }

  return n;
}

// ==================================================
// PACOTES PERSONALIZADOS DO ADMIN
// ==================================================

async function criarPacoteAdmin(nome, quantidade, destinatarios) {
  const x = await perfil();

  if (!x?.admin) {
    throw Error('Apenas o Admin pode criar pacotes');
  }

  const n = Number(quantidade);

  if (!Number.isInteger(n) || n < 1 || n > 30) {
    throw Error('Quantidade deve ser entre 1 e 30');
  }

  const reinosValidos = ['Drakmor', 'Solaris', 'Aetheryon'];

  if (
    !Array.isArray(destinatarios) ||
    !destinatarios.length ||
    destinatarios.some(r => !reinosValidos.includes(r))
  ) {
    throw Error('Destino inválido');
  }

  const cartas = await listarCartas();

  if (!cartas.length) {
    throw Error('Cadastre cartas antes de enviar');
  }

  const entregas = [];

  for (const reino of [...new Set(destinatarios)]) {
    const ids = Array.from(
      { length: n },
      () => cartas[Math.floor(Math.random() * cartas.length)].id
    );

    const ref = await addDoc(collection(db, 'pacotesEnviados'), {
      nome: String(nome || 'Presente do Admin').slice(0, 70),
      destinatario: reino,
      cartas: ids,
      status: 'pendente',
      criadoEm: Date.now()
    });

    entregas.push(ref.id);
  }

  return entregas;
}

async function listarPacotesRecebidos(reino) {
  const x = await perfil();

  if (!x || (x.reino !== reino && !x.admin)) {
    throw Error('Sem permissão');
  }

  const q = query(
    collection(db, 'pacotesEnviados'),
    where('destinatario', '==', reino)
  );

  const s = await getDocs(q);

  return s.docs
    .map(d => ({ id: d.id, ...d.data() }))
    .filter(p => p.status === 'pendente')
    .sort((a, b) => a.criadoEm - b.criadoEm);
}

async function resgatarPacote(id, reino) {
  const x = await perfil();

  if (!x || (x.reino !== reino && !x.admin)) {
    throw Error('Sem permissão');
  }

  return runTransaction(db, async tx => {
    const ref = doc(db, 'pacotesEnviados', id);
    const invRef = doc(db, 'inventarios', reino);

    const pacote = await tx.get(ref);
    const inv = await tx.get(invRef);

    if (!pacote.exists()) {
      throw Error('Pacote não encontrado');
    }

    const dados = pacote.data();

    if (dados.destinatario !== reino || dados.status !== 'pendente') {
      throw Error('Pacote já resgatado ou inválido');
    }

    const lista = inv.exists()
      ? [...(inv.data().cartas || [])]
      : [];

    for (const cartaId of dados.cartas) {
      const it = lista.find(
        z => String(z.idCarta) === String(cartaId)
      );

      if (it) {
        it.quantidade = Number(it.quantidade || 0) + 1;
      } else {
        lista.push({
          idCarta: cartaId,
          quantidade: 1,
          nivel: 1,
          xp: 0
        });
      }
    }

    tx.set(invRef, { cartas: lista });
    tx.update(ref, { status: 'resgatado' });

    return dados.cartas;
  });
}

// ==================================================
// PACOTE DIÁRIO
// ==================================================

const INTERVALO_DIARIO_MS = 24 * 60 * 60 * 1000;

const CHANCES_DIARIAS = [
  ['comum', 60],
  ['rara', 25],
  ['epica', 10],
  ['lendaria', 4],
  ['mitica', 1]
];

function normalizarRaridade(valor) {
  return String(valor || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

// Sorteia 3 cartas, respeitando as raridades.
// Cartas repetidas são permitidas.

function sortearCartasDiarias(cartas, quantidade = 3) {
  const grupos = new Map(
    CHANCES_DIARIAS.map(([r]) => [r, []])
  );

  for (const carta of cartas) {
    const r = normalizarRaridade(carta.raridade);

    if (
      grupos.has(r) &&
      carta.id !== undefined &&
      carta.id !== null
    ) {
      grupos.get(r).push(carta);
    }
  }

  const disponiveis = CHANCES_DIARIAS.filter(
    ([r]) => grupos.get(r).length
  );

  if (!disponiveis.length) {
    throw Error(
      'Nenhuma carta com raridade válida cadastrada no catálogo.'
    );
  }

  const totalPeso = disponiveis.reduce(
    (s, [, peso]) => s + peso,
    0
  );

  return Array.from({ length: quantidade }, () => {
    let sorteio = Math.random() * totalPeso;
    let grupo = disponiveis[disponiveis.length - 1][0];

    for (const [raridade, peso] of disponiveis) {
      sorteio -= peso;

      if (sorteio < 0) {
        grupo = raridade;
        break;
      }
    }

    const pool = grupos.get(grupo);

    return pool[
      Math.floor(Math.random() * pool.length)
    ].id;
  });
}

// Consulta quando o reino poderá abrir novamente.

async function estadoPacoteDiario(reino) {
  const x = await perfil();

  if (!x || x.admin || x.reino !== reino) {
    throw Error(
      'Entre com a conta do reino para abrir o pacote diário.'
    );
  }

  const snap = await getDoc(
    doc(db, 'pacotesDiarios', reino)
  );

  const ms =
    snap.exists() && snap.data().abertoEm?.toMillis
      ? snap.data().abertoEm.toMillis()
      : 0;

  return {
    proximoEm: ms ? ms + INTERVALO_DIARIO_MS : 0,
    agora: Date.now()
  };
}

// Abre o pacote e salva as três cartas e o horário
// na mesma transação do Firebase.

async function abrirPacoteDiario(reino) {
  const x = await perfil();

  if (!x || x.admin || x.reino !== reino) {
    throw Error(
      'Somente a conta do próprio reino pode abrir o pacote diário.'
    );
  }

  const catalogo = await listarCartas();
  const ids = sortearCartasDiarias(catalogo, 3);

  const ref = doc(db, 'pacotesDiarios', reino);
  const invRef = doc(db, 'inventarios', reino);

  await runTransaction(db, async tx => {
    const diario = await tx.get(ref);
    const inventarioAtual = await tx.get(invRef);

    const ultimo =
      diario.exists() && diario.data().abertoEm?.toMillis
        ? diario.data().abertoEm.toMillis()
        : 0;

    if (
      ultimo &&
      Date.now() < ultimo + INTERVALO_DIARIO_MS
    ) {
      const e = Error(
        'Pacote indisponível: aguarde a próxima abertura.'
      );

      e.proximoEm = ultimo + INTERVALO_DIARIO_MS;
      throw e;
    }

    const lista = inventarioAtual.exists()
      ? (inventarioAtual.data().cartas || []).map(c => ({ ...c }))
      : [];

    for (const id of ids) {
      const item = lista.find(
        c => String(c.idCarta) === String(id)
      );

      if (item) {
        item.quantidade = Number(item.quantidade || 0) + 1;
      } else {
        lista.push({
          idCarta: id,
          quantidade: 1,
          nivel: 1,
          xp: 0
        });
      }
    }

    if (lista.length > 500) {
      throw Error(
        'O inventário atingiu o limite de 500 tipos de cartas.'
      );
    }

    tx.set(invRef, { cartas: lista });

    tx.set(ref, {
      abertoEm: serverTimestamp()
    });
  });

  return ids;
}

// ==================================================
// DISPONIBILIZAR FUNÇÕES PARA AS PÁGINAS
// ==================================================

window.RB = {
  auth,
  db,
  ADMIN_UID,
  authReady,
  perfil,
  exigir,
  entrar,
  entrarReino,
  sair,
  listarCartas,
  salvarCarta,
  apagarCarta,
  inventario,
  adicionarCartas,
  importarCartas,
  criarPacoteAdmin,
  listarPacotesRecebidos,
  resgatarPacote,
  estadoPacoteDiario,
  abrirPacoteDiario,
  doc,
  getDoc,
  setDoc,
  onSnapshot
};
