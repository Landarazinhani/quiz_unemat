const fs = require('fs');
const path = require('path');

// Função para ler dados de um arquivo JSON
const lerJson = (arquivo) => {
  const caminho = path.join(__dirname, 'data', arquivo);

  try {
    if (!fs.existsSync(caminho)) {
      return {}; // Retorna objeto vazio se o arquivo não existir
    }

    const conteudo = fs.readFileSync(caminho, 'utf-8');
    return JSON.parse(conteudo || '{}'); // Evita erro se o arquivo estiver vazio
  } catch (err) {
    console.error(`Erro ao ler ${arquivo}:`, err);
    return {};
  }
};

// Função para escrever dados em um arquivo JSON
const escreverJson = (arquivo, dados) => {
  const caminho = path.join(__dirname, 'data', arquivo);

  try {
    fs.writeFileSync(caminho, JSON.stringify(dados, null, 2), 'utf-8');
  } catch (err) {
    console.error(`Erro ao escrever ${arquivo}:`, err);
  }
};

// Atualizar contadores de respostas
const atualizarContadorRespostas = (perguntaId, alternativaEscolhida) => {
  const resultados = lerJson('resultados.json');

  const pid = String(perguntaId); // Força a ser string (chave)

  if (!resultados[pid]) {
    resultados[pid] = { A: 0, B: 0, C: 0, D: 0 };
  }

  if (resultados[pid][alternativaEscolhida] !== undefined) {
    resultados[pid][alternativaEscolhida]++;
  } else {
    console.warn(`Alternativa inválida: ${alternativaEscolhida}`);
  }

  escreverJson('resultados.json', resultados);
};

// Atualizar contador de participantes
const atualizarContadorParticipantes = () => {
  const dados = lerJson('dados.json');

  if (!dados.participantes || typeof dados.participantes !== 'number') {
    dados.participantes = 0;
  }

  dados.participantes++;

  escreverJson('dados.json', dados);
};

// Simulação
atualizarContadorRespostas(1, 'A');
atualizarContadorParticipantes();

console.log("Contadores atualizados com sucesso!");
