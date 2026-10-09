import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-app.js';

import {
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut
} from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-auth.js';

import {
  getFirestore,
  doc,
  getDoc,
  getDocs,
  collection,
  setDoc,
  deleteDoc,
  runTransaction,
  onSnapshot,
  addDoc,
  query,
  where,
  serverTimestamp
} from 'https://www.gstatic.com/firebasejs/10.14.1/firebase-firestore.js';

// ==================================================
// CONFIGURAÇÃO DO FIREBASE
// ==================================================

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

// ==================================================
// LOGIN
// ==================================================

const authReady = new Promise(resolve => {
  const unsubscribe = onAuthStateChanged(auth, usuario => {
    unsubscribe();
    resolve(usuario);
  });
});

async function perfil() {
  await authReady;

  const usuario = auth.currentUser;

  if (!usuario) return null;

  if (usuario.uid === ADMIN_UID) {
    return {
      uid: usuario.uid,
      reino: 'Admin',
      admin: true
    };
  }

  const reino = Object.keys(CONTAS_REINO).find(
    nome => CONTAS_REINO[nome].uid === usuario.uid
  );

  return reino
    ? { uid: usuario.uid, reino, admin: false }
    : null;
}

async function exigir() {
  let usuario;

  try {
    usuario = await perfil();
  } catch (erro) {
    alert('Erro ao verificar login: ' + erro.message);
    location.replace('index.html');
    throw erro;
  }

  if (!usuario) {
    location.replace('index.html');
    throw Error('Login não autorizado');
  }

  localStorage.setItem('usuarioLogado', usuario.reino);

  return usuario;
}

async function entrarReino(reino, codigo) {
  if (!CONTAS_REINO[reino]) {
    throw Error('Reino inválido');
  }

  if (!codigo) {
    throw Error('Digite o código secreto');
  }

  await authReady;

  const credencial = await signInWithEmailAndPassword(
    auth,
    CONTAS_REINO[reino].email,
    codigo
  );

  if (credencial.user.uid !== CONTAS_REINO[reino].uid) {
    await signOut(auth);
    throw Error('Esta conta não corresponde ao reino escolhido');
  }

  localStorage.setItem('usuarioLogado', reino);
  localStorage.removeItem('reinoVisitante');

  location.href = 'painel.html';
}

async function entrar(email, senha, escolha) {
  await authReady;

  const credencial = await signInWithEmailAndPassword(
    auth,
    email,
    senha
  );

  if (
    escolha !== 'Admin' ||
    credencial.user.uid !== ADMIN_UID
  ) {
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
  const resultado = await getDocs(collection(db, 'cartas'));

  return resultado.docs
    .map(documento => documento.data())
    .sort((a, b) => Number(a.id) - Number(b.id));
}

async function salvarCarta(carta) {
  const usuario = await perfil();

  if (!usuario?.admin) {
    throw Error('Apenas o Admin pode cadastrar cartas');
  }

  await setDoc(
    doc(db, 'cartas', String(carta.id)),
    carta
  );
}

async function apagarCarta(id) {
  const usuario = await perfil();

  if (!usuario?.admin) {
    throw Error('Apenas o Admin pode excluir cartas');
  }

  await deleteDoc(doc(db, 'cartas', String(id)));
}

// ==================================================
// INVENTÁRIO
// ==================================================

async function inventario(reino) {
  const resultado = await getDoc(
    doc(db, 'inventarios', reino)
  );

  return resultado.exists()
    ? resultado.data().cartas || []
    : [];
}

async function adicionarCartas(reino, ids) {
  await runTransaction(db, async transacao => {
    const referencia = doc(db, 'inventarios', reino);
    const resultado = await transacao.get(referencia);

    const lista = resultado.exists()
      ? (resultado.data().cartas || []).map(item => ({ ...item }))
      : [];

    for (const id of ids) {
      const item = lista.find(
        carta => String(carta.idCarta) === String(id)
      );

      if (item) {
        item.quantidade = Number(item.quantidade || 0) + 1;
      } else {
        lista.push({
          idCarta: id,
          quantidade: 1,
          nivel: 0,
          xp: 0
        });
      }
    }

    transacao.set(referencia, { cartas: lista });
  });
}

// ==================================================
// IMPORTAR CARTAS ANTIGAS
// ==================================================

async function importarCartas() {
  const dados = JSON.parse(
    localStorage.getItem('cartasReinos') || '[]'
  );

  if (!Array.isArray(dados) || !dados.length) {
    throw Error('Nenhuma carta local encontrada neste navegador.');
  }

  const atuais = await listarCartas();

  const existentes = new Set(
    atuais.map(carta => String(carta.id))
  );

  let quantidade = 0;

  for (const carta of dados) {
    if (!existentes.has(String(carta.id))) {
      await salvarCarta(carta);
      quantidade++;
    }
  }

  return quantidade;
}

// ==================================================
// PACOTES PERSONALIZADOS DO ADMIN
// ==================================================

async function criarPacoteAdmin(nome, quantidade, destinatarios) {
  const usuario = await perfil();

  if (!usuario?.admin) {
    throw Error('Apenas o Admin pode criar pacotes');
  }

  const numero = Number(quantidade);

  if (
    !Number.isInteger(numero) ||
    numero < 1 ||
    numero > 30
  ) {
    throw Error('Quantidade deve ser entre 1 e 30');
  }

  if (
    !Array.isArray(destinatarios) ||
    !destinatarios.length ||
    destinatarios.some(reino => !reinos.includes(reino))
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
      { length: numero },
      () => cartas[Math.floor(Math.random() * cartas.length)].id
    );

    const referencia = await addDoc(
      collection(db, 'pacotesEnviados'),
      {
        nome: String(nome || 'Presente do Admin').slice(0, 70),
        destinatario: reino,
        cartas: ids,
        status: 'pendente',
        criadoEm: Date.now()
      }
    );

    entregas.push(referencia.id);
  }

  return entregas;
}

async function listarPacotesRecebidos(reino) {
  const usuario = await perfil();

  if (
    !usuario ||
    (usuario.reino !== reino && !usuario.admin)
  ) {
    throw Error('Sem permissão');
  }

  const consulta = query(
    collection(db, 'pacotesEnviados'),
    where('destinatario', '==', reino)
  );

  const resultado = await getDocs(consulta);

  return resultado.docs
    .map(documento => ({
      id: documento.id,
      ...documento.data()
    }))
    .filter(pacote => pacote.status === 'pendente')
    .sort((a, b) => a.criadoEm - b.criadoEm);
}

async function resgatarPacote(id, reino) {
  const usuario = await perfil();

  if (
    !usuario ||
    (usuario.reino !== reino && !usuario.admin)
  ) {
    throw Error('Sem permissão');
  }

  return runTransaction(db, async transacao => {
    const referencia = doc(db, 'pacotesEnviados', id);
    const referenciaInventario = doc(db, 'inventarios', reino);

    const pacote = await transacao.get(referencia);
    const inventarioAtual = await transacao.get(referenciaInventario);

    if (!pacote.exists()) {
      throw Error('Pacote não encontrado');
    }

    const dados = pacote.data();

    if (
      dados.destinatario !== reino ||
      dados.status !== 'pendente'
    ) {
      throw Error('Pacote já resgatado ou inválido');
    }

    const lista = inventarioAtual.exists()
      ? (inventarioAtual.data().cartas || []).map(item => ({ ...item }))
      : [];

    for (const idCarta of dados.cartas) {
      const item = lista.find(
        carta => String(carta.idCarta) === String(idCarta)
      );

      if (item) {
        item.quantidade = Number(item.quantidade || 0) + 1;
      } else {
        lista.push({
          idCarta,
          quantidade: 1,
          nivel: 0,
          xp: 0
        });
      }
    }

    transacao.set(referenciaInventario, { cartas: lista });

    transacao.update(referencia, {
      status: 'resgatado'
    });

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

function sortearCartasDiarias(cartas, quantidade = 3) {
  const grupos = new Map(
    CHANCES_DIARIAS.map(([raridade]) => [raridade, []])
  );

  for (const carta of cartas) {
    const raridade = normalizarRaridade(carta.raridade);

    if (
      grupos.has(raridade) &&
      carta.id !== undefined &&
      carta.id !== null
    ) {
      grupos.get(raridade).push(carta);
    }
  }

  const disponiveis = CHANCES_DIARIAS.filter(
    ([raridade]) => grupos.get(raridade).length
  );

  if (!disponiveis.length) {
    throw Error(
      'Nenhuma carta com raridade válida cadastrada no catálogo.'
    );
  }

  const pesoTotal = disponiveis.reduce(
    (total, [, peso]) => total + peso,
    0
  );

  return Array.from({ length: quantidade }, () => {
    let sorteio = Math.random() * pesoTotal;

    let raridadeEscolhida = disponiveis[
      disponiveis.length - 1
    ][0];

    for (const [raridade, peso] of disponiveis) {
      sorteio -= peso;

      if (sorteio < 0) {
        raridadeEscolhida = raridade;
        break;
      }
    }

    const grupo = grupos.get(raridadeEscolhida);

    return grupo[
      Math.floor(Math.random() * grupo.length)
    ].id;
  });
}

async function estadoPacoteDiario(reino) {
  const usuario = await perfil();

  if (
    !usuario ||
    usuario.admin ||
    usuario.reino !== reino
  ) {
    throw Error(
      'Entre com a conta do reino para abrir o pacote diário.'
    );
  }

  const resultado = await getDoc(
    doc(db, 'pacotesDiarios', reino)
  );

  const horario = (
    resultado.exists() &&
    resultado.data().abertoEm?.toMillis
  )
    ? resultado.data().abertoEm.toMillis()
    : 0;

  return {
    proximoEm: horario
      ? horario + INTERVALO_DIARIO_MS
      : 0,
    agora: Date.now()
  };
}

async function abrirPacoteDiario(reino) {
  const usuario = await perfil();

  if (
    !usuario ||
    usuario.admin ||
    usuario.reino !== reino
  ) {
    throw Error(
      'Somente a conta do próprio reino pode abrir o pacote diário.'
    );
  }

  const catalogo = await listarCartas();
  const ids = sortearCartasDiarias(catalogo, 3);

  const referenciaDiario = doc(db, 'pacotesDiarios', reino);
  const referenciaInventario = doc(db, 'inventarios', reino);

  await runTransaction(db, async transacao => {
    const diario = await transacao.get(referenciaDiario);
    const inventarioAtual = await transacao.get(referenciaInventario);

    const ultimo = (
      diario.exists() &&
      diario.data().abertoEm?.toMillis
    )
      ? diario.data().abertoEm.toMillis()
      : 0;

    if (
      ultimo &&
      Date.now() < ultimo + INTERVALO_DIARIO_MS
    ) {
      const erro = Error(
        'Pacote indisponível: aguarde a próxima abertura.'
      );

      erro.proximoEm = ultimo + INTERVALO_DIARIO_MS;

      throw erro;
    }

    const lista = inventarioAtual.exists()
      ? (inventarioAtual.data().cartas || []).map(item => ({ ...item }))
      : [];

    for (const id of ids) {
      const item = lista.find(
        carta => String(carta.idCarta) === String(id)
      );

      if (item) {
        item.quantidade = Number(item.quantidade || 0) + 1;
      } else {
        lista.push({
          idCarta: id,
          quantidade: 1,
          nivel: 0,
          xp: 0
        });
      }
    }

    if (lista.length > 500) {
      throw Error(
        'O inventário atingiu o limite de 500 tipos de cartas.'
      );
    }

    transacao.set(referenciaInventario, {
      cartas: lista
    });

    transacao.set(referenciaDiario, {
      abertoEm: serverTimestamp()
    });
  });

  return ids;
}

// ==================================================
// SISTEMA DE XP E EVOLUÇÃO
// ==================================================

const NIVEL_MAXIMO = 30;

const INTERVALO_TREINO_MS = 4 * 60 * 60 * 1000;

const XP_TREINO = 100;

// XP necessário para passar ao próximo nível.

function xpNecessario(nivel) {
  const numero = Math.max(
    0,
    Math.min(NIVEL_MAXIMO, Math.floor(Number(nivel) || 0))
  );

  if (numero >= NIVEL_MAXIMO) {
    return 0;
  }

  return 100 + numero * 25;
}

// Procura a evolução cadastrada pelo Admin.

function etapaEvolucao(carta, nivel) {
  const evolucoes = Array.isArray(carta?.evolucoes)
    ? carta.evolucoes
    : [];

  return evolucoes.find(
    evolucao => Number(evolucao.nivel) === Number(nivel)
  ) || null;
}

// Calcula os atributos da carta conforme o nível.

function atributosCarta(carta, item) {
  const nivel = Math.max(
    0,
    Math.min(NIVEL_MAXIMO, Number(item?.nivel ?? 0))
  );

  const primeira = etapaEvolucao(carta, 11);
  const segunda = etapaEvolucao(carta, 21);

  const forma = nivel >= 21
    ? (segunda || primeira)
    : nivel >= 11
      ? primeira
      : null;

  const bonus = forma?.bonus || {};

  const fator = 1 + nivel * 0.015;

  const atributo = nome => {
    const valorBase = Number(carta?.[nome]) || 0;
    const valorBonus = Number(bonus[nome]) || 0;

    return Math.round(valorBase * fator + valorBonus);
  };

  return {
    nivel,
    nome: forma?.nome || carta.nome,
    imagem: forma?.imagem || carta.imagem,
    fundo: forma?.fundo || carta.fundo,
    raridade: forma?.raridade || carta.raridade,
    vida: atributo('vida'),
    ataque: atributo('ataque'),
    defesa: atributo('defesa'),
    velocidade: atributo('velocidade')
  };
}

// Confere se o usuário pertence ao reino.

function validarReinoDaCarta(usuario, reino) {
  if (
    !usuario ||
    usuario.admin ||
    usuario.reino !== reino
  ) {
    throw Error(
      'Entre com a conta do próprio reino para treinar ou evoluir.'
    );
  }
}

// ==================================================
// TREINAMENTO
// ==================================================
// 100 XP por treino.
// Intervalo de 4 horas por tipo de carta.
// Nível máximo: 30.

async function treinarCarta(reino, idCarta) {
  validarReinoDaCarta(await perfil(), reino);

  const referenciaInventario = doc(db, 'inventarios', reino);
  const referenciaCarta = doc(db, 'cartas', String(idCarta));

  return runTransaction(db, async transacao => {
    const inventarioAtual = await transacao.get(
      referenciaInventario
    );

    const registroCarta = await transacao.get(
      referenciaCarta
    );

    if (!registroCarta.exists()) {
      throw Error('Carta não encontrada no catálogo.');
    }

    const carta = registroCarta.data();

    const lista = inventarioAtual.exists()
      ? (inventarioAtual.data().cartas || []).map(item => ({ ...item }))
      : [];

    const item = lista.find(
      cartaInventario =>
        String(cartaInventario.idCarta) === String(idCarta)
    );

    if (!item || Number(item.quantidade || 0) < 1) {
      throw Error('Você não possui esta carta.');
    }

    let nivel = Math.max(
      0,
      Math.min(30, Number(item.nivel ?? 0))
    );

    let xp = Math.max(0, Number(item.xp) || 0);

    if (nivel >= NIVEL_MAXIMO) {
      throw Error('Esta carta já está no nível máximo.');
    }

    const bloqueado = (
      nivel === 10 && etapaEvolucao(carta, 11)
    ) || (
      nivel === 20 && etapaEvolucao(carta, 21)
    );

    if (bloqueado && xp >= xpNecessario(nivel)) {
      throw Error(
        'XP completo. Evolua esta carta para continuar treinando.'
      );
    }

    const agora = Date.now();
    const ultimoTreino = Number(item.ultimoTreino || 0);

    if (
      ultimoTreino &&
      agora < ultimoTreino + INTERVALO_TREINO_MS
    ) {
      throw Error(
        'Treino indisponível. Aguarde 4 horas desde o último treino.'
      );
    }

    xp += XP_TREINO;

    while (
      nivel < NIVEL_MAXIMO &&
      xp >= xpNecessario(nivel)
    ) {
      const exigeEvolucao = (
        nivel === 10 && etapaEvolucao(carta, 11)
      ) || (
        nivel === 20 && etapaEvolucao(carta, 21)
      );

      if (exigeEvolucao) {
        xp = xpNecessario(nivel);
        break;
      }

      xp -= xpNecessario(nivel);
      nivel++;

      const chegouNaEvolucao = (
        nivel === 10 && etapaEvolucao(carta, 11)
      ) || (
        nivel === 20 && etapaEvolucao(carta, 21)
      );

      if (chegouNaEvolucao) {
        xp = Math.min(xp, xpNecessario(nivel));
        break;
      }
    }

    item.nivel = nivel;
    item.xp = nivel >= NIVEL_MAXIMO ? 0 : xp;
    item.ultimoTreino = agora;

    transacao.set(referenciaInventario, {
      cartas: lista
    });

    return {
      nivel: item.nivel,
      xp: item.xp,
      recebido: XP_TREINO
    };
  });
}

// ==================================================
// EVOLUIR CARTA
// ==================================================
// Nível 10 -> 11: padrão 3 duplicatas.
// Nível 20 -> 21: padrão 5 duplicatas.
// O Admin poderá alterar esses valores em cada carta.

async function evoluirCarta(reino, idCarta) {
  validarReinoDaCarta(await perfil(), reino);

  const referenciaInventario = doc(db, 'inventarios', reino);
  const referenciaCarta = doc(db, 'cartas', String(idCarta));

  return runTransaction(db, async transacao => {
    const inventarioAtual = await transacao.get(
      referenciaInventario
    );

    const registroCarta = await transacao.get(
      referenciaCarta
    );

    if (!registroCarta.exists()) {
      throw Error('Carta não encontrada no catálogo.');
    }

    const carta = registroCarta.data();

    const lista = inventarioAtual.exists()
      ? (inventarioAtual.data().cartas || []).map(item => ({ ...item }))
      : [];

    const item = lista.find(
      cartaInventario =>
        String(cartaInventario.idCarta) === String(idCarta)
    );

    if (!item) {
      throw Error('Carta não encontrada no inventário.');
    }

    const nivel = Number(item.nivel ?? 0);

    if (nivel !== 10 && nivel !== 20) {
      throw Error(
        'A evolução exige que a carta esteja no nível 10 ou 20.'
      );
    }

    const proximoNivel = nivel + 1;

    const evolucao = etapaEvolucao(carta, proximoNivel);

    if (!evolucao) {
      throw Error(
        'O Admin ainda não cadastrou essa evolução.'
      );
    }

    const padraoDuplicatas = proximoNivel === 11 ? 3 : 5;

    const duplicatasNecessarias = Math.max(
      0,
      Math.floor(
        Number(evolucao.duplicatas ?? padraoDuplicatas)
      )
    );

    const quantidade = Number(item.quantidade || 0);

    if (quantidade < duplicatasNecessarias + 1) {
      throw Error(
        `Você precisa de ${duplicatasNecessarias} cópias extras. ` +
        `Possui ${Math.max(0, quantidade - 1)}.`
      );
    }

    const xpExigido = xpNecessario(nivel);

    if (Number(item.xp || 0) < xpExigido) {
      throw Error(
        `Faltam ${xpExigido - Number(item.xp || 0)} XP para evoluir.`
      );
    }

    // Consome apenas as duplicatas.
    // A carta principal permanece no inventário.

    item.quantidade = quantidade - duplicatasNecessarias;

    item.xp = Number(item.xp || 0) - xpExigido;

    item.nivel = proximoNivel;

    transacao.set(referenciaInventario, {
      cartas: lista
    });

    return {
      nivel: proximoNivel,
      quantidade: item.quantidade,
      nome: evolucao.nome || carta.nome
    };
  });
}

// ==================================================
// DISPONIBILIZAR FUNÇÕES PARA O SITE
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

  // Cartas
  listarCartas,
  salvarCarta,
  apagarCarta,

  // Inventário
  inventario,
  adicionarCartas,
  importarCartas,

  // Pacotes
  criarPacoteAdmin,
  listarPacotesRecebidos,
  resgatarPacote,
  estadoPacoteDiario,
  abrirPacoteDiario,

  // XP e evolução
  xpNecessario,
  atributosCarta,
  treinarCarta,
  evoluirCarta,

  // Firebase
  doc,
  getDoc,
  setDoc,
  onSnapshot
};
