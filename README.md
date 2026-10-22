# Hackathon Core Starter Kit - arquitetura lanciare (https://github.com/devDaviHtrb/AuctionProject) 🚀

Starter kit modular e acelerado em **Python (Flask)** desenvolvido para criar aplicações completas rapidamente durante hackathons.

## ✨ O que já vem pronto:

1. **Autenticação Completa**:
   - Cadastro multi-etapas com suporte a **Pessoa Física (PF)** e **Pessoa Jurídica (PJ)**.
   - Login por email ou nome de usuário.
   - Validações completas de CPF, CNPJ, RG, CEP e telefone.
   - Integração com **Google OAuth 2.0**.
   - Verificação de email por tokens temporários com auto-expiração.
   - Suporte a autenticação em duas etapas (2FA).
   - Redefinição e recuperação de senha.
   - Sessões seguras com cookies criptografados via **Fernet**.

2. **Controle de Acesso por Diretórios (Zero Boilerplate)**:
   - Pastas `public/`: Acesso livre.
   - Pastas `common/`: Acesso restrito a usuários autenticados (redireciona para login se não autenticado).
   - Pastas `admin/`: Acesso restrito a administradores (`admin_user == True`).

3. **WebSockets em Tempo Real (Flask-SocketIO)**:
   - Handlers automáticos para gerenciamento de salas (`join_room`, `leave_room`).
   - Disparo de mensagens (`send_message`) e broadcast.
   - Testador de WebSockets interativo integrado na tela inicial (`Index.html`).

4. **Banco de Dados com Auto-Discovery**:
   - Criação automática de tabelas a partir de qualquer modelo em `myapp/models/`.
   - SQLite como fallback zero-config (`sqlite:///hackathon.db`) ou PostgreSQL/MySQL configurável.

5. **Console Administrativo Web (`/admin`)**:
   - Terminal interativo no navegador para consultas e modificações SQL diretas.
   - Ação de force logout por usuário ou global.

---

## 🚀 Como Rodar o Projeto

1. **Ative o ambiente virtual**:

   ```powershell
   .venv\Scripts\activate
   ```

2. **Configure o arquivo `.env`**:
   O arquivo `.env` já vem pré-configurado com SQLite. Se desejar usar PostgreSQL ou outros serviços (Google OAuth, Cloudinary, Gmail), configure as chaves em `.env` (baseado no `.env.example`).

3. **Inicie o servidor**:
   ```powershell
   python app.py
   ```
   Acesse no navegador: `http://localhost:5000`

---

## 🛠️ Como Adicionar Funcionalidades

- **Nova Rota**: Crie um arquivo em `myapp/routes/{actions|pages}/{public|common|admin}/NomeDaRota.py` com um `Blueprint`. Ela será registrada automaticamente!
- **Novo Modelo**: Crie uma classe em `myapp/models/NomeDoModelo.py` herdando de `db.Model`. A tabela será criada automaticamente!
- **Novo Evento WebSocket**: Adicione handlers em `myapp/sockets/` usando `@socket_io.on("nome_do_evento")`.

Consulte o arquivo `.agents/skills/hackathon-system-guide/SKILL.md` ou `GEMINI.md` para o guia técnico completo.

---

# Hackathon 2026 — CitaDelas: Análise e Recomendação de Referências Científicas de Autoria Feminina

<img width="825" height="291" alt="citadelas logo recortada" src="https://github.com/user-attachments/assets/5ddf6155-3bf1-4349-af35-128b52c9bcb7" />

## 1. Sobre o projeto

O projeto tem como objetivo auxiliar pesquisadores na identificação de referências científicas relevantes para seus manuscritos, contribuindo para a construção de uma bibliografia mais alinhada ao tema da pesquisa e incentivando a representatividade feminina na autoria dos trabalhos recomendados.

A aplicação combina inteligência artificial, busca bibliográfica, processamento de linguagem natural e métricas de avaliação para analisar um artigo submetido e recomendar trabalhos potencialmente relevantes.

O sistema utiliza o Gemini para compreender o contexto do manuscrito, a OpenAlex para localizar trabalhos acadêmicos e o Demografix para estimar a composição de gênero da autoria. Os candidatos recuperados são avaliados por meio de métricas de similaridade, importância, atualidade, relevância por citações e composição de gênero.

## 2. Estrutura de pastas

```text
.
├── .agents/
│   └── skills/
│       └── hackathon-system-guide/
└── myapp/
    ├── models/
    ├── repositories/
    ├── routes/
    │   ├── actions/
    │   │   ├── admin/
    │   │   ├── common/
    │   │   └── public/
    │   └── pages/
    │       ├── admin/
    │       ├── common/
    │       └── public/
    ├── services/
    ├── setup/
    ├── sockets/
    ├── static/
    │   ├── js/
    │   │   ├── api/
    │   │   ├── components/
    │   │   ├── interactivity/
    │   │   ├── JsClass/
    │   │   ├── mains/
    │   │   ├── sockets/
    │   │   ├── ui/
    │   │   └── validations/
    │   └── styles/
    │       ├── citadelas/
    │       └── components/
    ├── templates/
    │   └── components/
    │       └── citadelas/
    └── utils/
        ├── gemini/
        └── Validations/
```

### Responsabilidades dos diretórios

| Diretório         | Responsabilidade                                                                                   |
| ----------------- | -------------------------------------------------------------------------------------------------- |
| `models/`         | Organização dos modelos de dados da aplicação.                                                     |
| `repositories/`   | Organização das operações de acesso e persistência de dados.                                       |
| `routes/actions/` | Rotas relacionadas a ações da aplicação, organizadas por contexto de acesso.                       |
| `routes/pages/`   | Rotas relacionadas às páginas da aplicação, organizadas por contexto de acesso.                    |
| `services/`       | Implementação da lógica de negócio e das integrações principais.                                   |
| `setup/`          | Configuração e inicialização de componentes da aplicação.                                          |
| `sockets/`        | Componentes relacionados à comunicação por sockets.                                                |
| `static/js/`      | Código JavaScript do frontend, incluindo chamadas à API, componentes, interatividade e validações. |
| `static/styles/`  | Estilos visuais da aplicação.                                                                      |
| `templates/`      | Templates utilizados na renderização das páginas.                                                  |
| `utils/`          | Recursos auxiliares e utilitários compartilhados.                                                  |
| `.agents/skills/` | Instruções e recursos de apoio ao desenvolvimento com agentes.                                     |

## 3. Fluxo de execução da pipeline

O processamento principal começa no endpoint `POST /pdf/page`, responsável por receber o arquivo enviado pelo frontend, coordenar os serviços de análise e devolver o contexto do manuscrito junto às recomendações encontradas.

### Etapa 1 — Recebimento do arquivo

A rota `GetPdfPage`, definida em um Blueprint Flask, recebe o arquivo por meio do campo multipart `pdf_file`.

Antes de iniciar o processamento, verifica se o arquivo foi enviado e se possui um nome. Caso contrário, retorna um erro HTTP `400`, informando que nenhum arquivo foi enviado.

### Etapa 2 — Extração do texto

O conteúdo binário do arquivo é enviado para `extract_file_text`, localizado em `ExtractTextService.py`.

A função extrai o texto de arquivos PDF ou TXT e o transforma em uma string, que será utilizada pelas etapas seguintes.

O texto completo é armazenado no campo `all_content`.

### Etapa 3 — Análise contextual com o Gemini

A rota chama `geminiService.analyze_article(all_content)`, localizada em `GeminiService.py`.

O Gemini interpreta o conteúdo e retorna uma estrutura validada pelo `ArticleContextSchema`, contendo informações como:

- título;
- objetivo da pesquisa;
- área de pesquisa;
- resumo;
- tópicos relevantes e palavras-chave;
- referências já existentes.

Essa análise transforma o texto integral em um contexto estruturado, que será utilizado na busca de trabalhos acadêmicos.

### Etapa 4 — Busca de candidatos na OpenAlex

A rota organiza o texto integral e a análise contextual em um objeto `pdf_data`:

- `all_content`: texto extraído do arquivo;
- `article_analysis`: análise contextual produzida pelo Gemini.

Em seguida, chama `calculate_articles_scores(pdf_data)`, localizado no módulo servies em `article.py`.

Esse serviço utiliza o `AlexService` para consultar trabalhos acadêmicos na OpenAlex com base nos temas e nas palavras-chave identificados na análise contextual.

### Etapa 5 — Tratamento e filtragem dos candidatos

O método `buscar_artigos_para_comparacao` executa a busca bibliográfica e prepara os candidatos para a avaliação.

O processamento inclui a remoção de duplicatas, a exclusão de referências já existentes no manuscrito e a filtragem por composição de gênero da autoria.

Na chamada utilizada pela pipeline, os parâmetros são:

- limite de autoria feminina: `25%`;
- país de referência: `BR`;
- quantidade de fallback: `5`.

O filtro principal mantém candidatos cujo percentual estimado de autoria feminina seja **maior que 25%**. Caso nenhum candidato atenda ao limite, o fallback permite recuperar candidatos com maiores percentuais, conforme a implementação do serviço.

Os resultados são normalizados para padronizar os campos utilizados pelas funções de avaliação.

### Etapa 6 — Cálculo da similaridade

Para cada candidato selecionado, `calculate_score` chama `calculate_article_similarity`.

A função compara o manuscrito original com o artigo candidato utilizando três campos:

- título;
- resumo;
- palavras-chave.

A similaridade combina uma abordagem semântica, baseada em embeddings, com uma abordagem lexical, baseada em TF-IDF e similaridade do cosseno.

O resultado é convertido para uma escala de 0 a 100 e inclui tanto a pontuação geral de similaridade quanto as pontuações individuais por campo.

### Etapa 7 — Avaliação da importância

O módulo chama `calculate_article_importance`, que prepara uma representação textual do candidato e solicita ao Gemini uma avaliação de importância em relação ao manuscrito original.

A resposta estruturada inclui a pontuação de importância, a justificativa, as evidências, a incerteza e informações relacionadas à utilização de citações.

O resultado é convertido para um dicionário quando necessário, permitindo acessar a pontuação pelo campo `importance_score`.

### Etapa 8 — Cálculo das demais métricas

Além da similaridade e da importância, o sistema calcula:

- **Atualidade:** pontuação baseada no tempo desde a publicação, com decaimento exponencial.
- **Relevância:** pontuação baseada no número de citações do trabalho.
- **Composição de gênero:** percentual estimado de autoria feminina.

Essas métricas são calculadas pelas funções `calculate_article_present`, `calculate_article_relevance` e `calculate_article_genre_compose`.

### Etapa 9 — Composição da pontuação final

A função `calculate_score` reúne os componentes e calcula uma pontuação geral ponderada.

Os pesos configurados são:

| Critério             | Peso |
| -------------------- | ---: |
| Similaridade         |  40% |
| Importância          |  25% |
| Relevância           |  15% |
| Atualidade           |  10% |
| Composição de gênero |  10% |

A pontuação geral é calculada pela soma da pontuação de cada critério multiplicada pelo respectivo peso.

### Etapa 10 — Montagem e retorno da resposta

Os candidatos avaliados são organizados em uma lista de recomendações. Cada item contém os dados bibliográficos do candidato e os resultados de sua avaliação.

A rota prepara também um objeto `source`, com as principais informações do manuscrito original, e retorna ambos em uma resposta JSON.

A resposta final possui a seguinte estrutura geral:

```json
{
  "source": {
    "title": "Título do manuscrito",
    "research_area": "Área de pesquisa",
    "research_objective": "Objetivo da pesquisa",
    "summary": "Resumo do manuscrito"
  },
  "recommendations": [
    {
      "article": {
        "article_data": {
          "title": "Título do artigo recomendado",
          "year": 2024,
          "doi": "DOI, quando disponível"
        },
        "score_data": {
          "similarity": 85.0,
          "importance": 80.0,
          "present": 90.0,
          "relevance": 70.0,
          "genre_compose": 40.0,
          "total": 77.0,
          "correction": {}
        }
      }
    }
  ]
}
```

O JSON acima é um exemplo ilustrativo do formato da resposta, não um resultado real. Os valores são fictícios, e `article_data` pode conter outros campos normalizados da OpenAlex. O conteúdo de `correction` corresponde à avaliação estruturada de importância retornada pelo Gemini.

## 4. Endpoint principal

### `POST /pdf/page`

Responsável por receber o arquivo, executar a análise do manuscrito e retornar as recomendações.

**Entrada:** arquivo enviado no campo `pdf_file`, em uma requisição multipart/form-data.

**Validação:** se o arquivo estiver ausente ou sem nome, a rota retorna HTTP `400`.

**Processamento:**

1. Extrai o texto do arquivo.
2. Analisa o artigo com o Gemini.
3. Busca e avalia referências candidatas.
4. Monta os dados do manuscrito original.
5. Retorna o contexto e as recomendações em JSON.

**Resposta de sucesso:** objeto JSON com os campos `source` e `recommendations`.

O endpoint não realiza persistência de resultados no código apresentado.

## 5. Serviços principais

### 5.1. `GeminiService.py`

Responsável pela integração com o Google Gemini para análise contextual e avaliação da importância dos artigos.

#### `analyze_article(article: str)`

Recebe o texto completo do manuscrito e solicita uma análise estruturada.

A resposta é validada pelo `ArticleContextSchema`, garantindo que os campos estejam de acordo com o formato definido pela aplicação.

#### `article_importance(article_a, article_b)`

Avalia a importância de um artigo candidato em relação ao contexto de outro artigo.

A resposta é validada pelo `ImportanceAnalysisSchema`, que define a estrutura da pontuação, justificativa, evidências, incerteza e informações de apoio.

#### Configurações

- `Config.GEMINI_API_KEY`: credencial de acesso.
- `Config.GEMINI_MODEL`: modelo utilizado.
- Temperatura configurada: `0.2`.
- Limite de saída configurado: `8192` tokens.
- Prompts definidos em `GeminiPrompt.py`.

### 5.2. `GeminiSchema.py`

Define os modelos de dados utilizados para validar as respostas estruturadas do Gemini.

#### `TopicPurpose`

Enum que classifica os tópicos em metodologia, trabalhos relacionados, referencial teórico ou contextualização.

#### `TopicSchema`

Representa um tópico da pesquisa, com tema, descrição, palavras-chave e finalidade.

#### `ExistingReference`

Representa uma referência já presente no manuscrito, com título, autores e campos opcionais de DOI e ano.

#### `ArticleContextSchema`

Representa a análise contextual do artigo, incluindo título, objetivo, área de pesquisa, resumo, tópicos e referências existentes.

#### `EvidenceSchema`

Define uma evidência textual e a explicação de sua relevância para a avaliação.

#### `CitationLocationSchema`

Define informações de localização e contexto de uma citação, como página, linha, palavra, citação-âncora, função e justificativa.

#### `ImportanceAnalysisSchema`

Define a resposta da avaliação de importância, incluindo pontuação, parâmetros, justificativa, evidências, incerteza e informações sobre o uso de citações.

### 5.3. `OpenAlex.py` — `AlexService`

Responsável por buscar trabalhos acadêmicos na OpenAlex e preparar os resultados para a avaliação.

#### `buscar(...)`

Recebe o contexto da pesquisa e executa consultas bibliográficas com base nos temas e nas palavras-chave.

Suporta preferências de busca relacionadas a período de publicação, idioma, acesso aberto, presença de resumo e quantidade de resultados.

Também contempla tratamento de falhas de rede, deduplicação e exclusão de referências já existentes.

#### `buscar_artigos_para_comparacao(...)`

Combina a busca de candidatos com o filtro de composição de gênero e prepara os artigos para as etapas posteriores.

#### `filtrar_autoria_feminina(...)`

Filtra os candidatos com base no percentual estimado de autoria feminina, com possibilidade de fallback quando nenhum resultado atende ao limite principal.

#### Normalização dos candidatos

O método `_normalizar_candidato` organiza os campos bibliográficos utilizados pela avaliação, como identificador OpenAlex, DOI, URL, título, ano, resumo, número de citações, palavras-chave, autores, origem dos tópicos e dados de gênero.

O `AlexService` é responsável pela busca e pelo tratamento dos dados bibliográficos; as métricas de avaliação final são calculadas no módulo `article.py`.

### 5.4. `article.py`

Responsável por calcular as métricas de avaliação dos artigos candidatos e montar os resultados utilizados pela pipeline.

#### `calculate_article_similarity(article_a, article_b)`

Compara título, resumo e palavras-chave dos artigos.

Os pesos por campo são:

| Campo          | Peso |
| -------------- | ---: |
| Título         |  20% |
| Resumo         |  45% |
| Palavras-chave |  35% |

Cada campo combina similaridade semântica e lexical:

| Método    | Peso |
| --------- | ---: |
| Semântico |  80% |
| Lexical   |  20% |

A abordagem semântica utiliza o modelo `paraphrase-multilingual-MiniLM-L12-v2`. A abordagem lexical utiliza TF-IDF, unigramas, bigramas e similaridade do cosseno.

A função retorna a pontuação geral e as pontuações por campo.

#### `calculate_article_importance(...)`

Converte os dados do artigo candidato em texto e encaminha a comparação para o Gemini, chamando o serviço `article_importance` do `GeminiService.py`

#### `calculate_article_present(...)`

Calcula a atualidade do artigo por meio de decaimento exponencial. Na chamada atual de `calculate_score`, o parâmetro `h` é `5` anos.

#### `calculate_article_relevance(...)`

Calcula a relevância com base no número de citações. Na chamada atual de `calculate_score`, a base utilizada é `10`.

A pontuação é limitada ao intervalo de 0 a 100.

#### `calculate_article_genre_compose(...)`

Obtém o percentual estimado de autoria feminina dos dados associados ao candidato.

#### `calculate_score(...)`

Executa as avaliações e calcula a pontuação geral ponderada. Também devolve os componentes individuais e a resposta completa da avaliação de importância no campo `correction`.

#### `calculate_articles_scores(...)`

Coordena a avaliação dos candidatos recuperados pelo `AlexService`, respeitando os parâmetros de limite e deslocamento (`limit` e `offset`).

Cada resultado é organizado com os dados do artigo e suas pontuações.

### 5.5. `ExtractTextService.py`

Responsável pela extração de texto dos arquivos recebidos.

A função `extract_file_text(byte_content, filename)` processa arquivos PDF com `pypdf` e arquivos TXT com decodificação UTF-8. O conteúdo das páginas de um PDF é reunido em uma única string.

A função não apresenta implementação de OCR; portanto, documentos digitalizados exclusivamente como imagens podem não gerar texto extraível.

### 5.6. `GenderizeNames.py`

Responsável por estimar informações de gênero associadas aos nomes dos autores utilizando o serviço Demografix.

#### Funções principais

- `genderize_name`: consulta individual de um nome.
- `genderize_names`: consulta de nomes em lote.
- `female_authorship_share`: calcula a proporção de autores classificados como femininos.
- `analyze_authors`: consolida contagens, percentuais e previsões individuais.

O limiar de classificação feminina está definido como `0.8`. Uma previsão feminina só é contabilizada quando a probabilidade estimada é igual ou superior a esse valor.

O código contabiliza previsões masculinas sem aplicar o mesmo limiar. Por isso, os percentuais representam estimativas computacionais, não a confirmação da identidade de gênero dos autores.

A integração depende de `Config.DEMOGRAFIX_API_KEY`.

## 6. Tecnologias e integrações

| Tecnologia            | Utilização                                                                     |
| --------------------- | ------------------------------------------------------------------------------ |
| Python                | Linguagem principal do backend.                                                |
| Flask                 | Framework web e implementação do endpoint.                                     |
| Pydantic              | Validação dos dados estruturados. Montagem dos Schemas de resposta estruturada |
| Google Gemini         | Análise contextual e avaliação de importância.                                 |
| OpenAlex              | Busca bibliográfica e metadados acadêmicos.                                    |
| Demografix            | Estimativa de gênero associada aos nomes dos autores.                          |
| Sentence Transformers | Embeddings para comparação semântica.                                          |
| scikit-learn          | TF-IDF e similaridade do cosseno.                                              |
| pypdf                 | Extração de texto de PDFs.                                                     |
