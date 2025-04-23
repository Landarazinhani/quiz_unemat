const fs = require('fs');
const path = require('path');

// Função para ler dados de um arquivo JSON
const lerJson = (arquivo) => {
  const caminho = path.join(__dirname, 'data', arquivo); // Alterado para buscar na pasta 'data'
  return JSON.parse(fs.readFileSync(caminho, 'utf-8'));
};

// Função para escrever dados em um arquivo JSON
const escreverJson = (arquivo, dados) => {
  const caminho = path.join(__dirname, 'data', arquivo); // Alterado para salvar na pasta 'data'
  fs.writeFileSync(caminho, JSON.stringify(dados, null, 2));
};

// Inicializando contadores
const atualizarContadorRespostas = (perguntaId, alternativaEscolhida) => {
  // Carregar o arquivo de resultados
  const resultados = lerJson('resultados.json');

  // Verificar se já existe esse contador para a pergunta
  if (!resultados[perguntaId]) {
    resultados[perguntaId] = { A: 0, B: 0, C: 0, D: 0 };
  }

  // Incrementar o contador da alternativa escolhida
  if (resultados[perguntaId][alternativaEscolhida] !== undefined) {
    resultados[perguntaId][alternativaEscolhida]++;
  }

  // Salvar os resultados atualizados
  escreverJson('resultados.json', resultados);
};

// Inicializando o contador de participantes
const atualizarContadorParticipantes = () => {
  // Carregar o arquivo de dados
  const dados = lerJson('dados.json');

  // Incrementar o número de participantes
  dados.participantes++;

  // Salvar os dados atualizados
  escreverJson('dados.json', dados);
};

// Simulação de respostas e registro de participantes
// Atualizar respostas para a pergunta 1, alternativa A
atualizarContadorRespostas(1, 'A');

// Atualizar o contador de participantes
atualizarContadorParticipantes();

console.log("Contadores atualizados com sucesso!");
