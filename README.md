# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
<a href= "https://www.fiap.com.br/"><img src="assets/logo-fiap.png" alt="FIAP - Faculdade de Informática e Admnistração Paulista" border="0" width=40% height=40%></a>
</p>

<br>

# FarmTech Solutions — Monitor de Perdas na Colheita de Cana-de-Açúcar

## Integrantes:
- <a href="#">Raiane Sirlene da Silva — RM575984</a>
- <a href="#">Rodrigo Textor de Textor — RM574243</a>
- <a href="#">Pedro Victor Pires — RM575181</a>
- <a href="#">Nome do integrante 4 — RM000000</a>
- <a href="#">Nome do integrante 5 — RM000000</a>

## Descrição

### A dor do agronegócio que escolhemos

O Brasil é o maior produtor mundial de cana-de-açúcar, mas perde uma parte significativa
da produção **dentro do próprio campo, no momento da colheita**. Segundo a SOCICANA, a
colheita mecanizada pode perder **até 15% da produção**, enquanto na colheita manual as
perdas raramente passam de **5%**. No estado de São Paulo, isso representa um prejuízo anual
estimado em **R$ 20 milhões** para o setor.

O problema é que, na maioria das propriedades, essa perda **não é medida de forma
sistemática**: o produtor sabe que perdeu, mas não sabe *quanto*, *em qual talhão*, *com qual
máquina* e *por quê*. Sem esse dado, não há como agir.

### A solução

O **Monitor de Perdas na Colheita** é um sistema em Python, operado pelo prompt de comando,
que registra cada colheita e transforma os números em decisão:

1. O produtor informa o talhão, o tipo de colheita (manual ou mecanizada), a área, a
   produtividade estimada e o que foi efetivamente colhido.
2. O sistema calcula a **perda em toneladas, em percentual e em reais** (com o preço da
   tonelada configurável).
3. A perda é **classificada** em 🟢 aceitável, 🟡 atenção ou 🔴 crítica, com limites
   diferentes para colheita manual e mecanizada (configuráveis em JSON).
4. Tudo fica gravado no **banco de dados Oracle** da FIAP.

### Onde está a inovação

Em vez de só exibir um número, o sistema **aponta a provável causa e o que fazer**:

- **Diagnóstico da colhedora:** para colheitas mecanizadas, o sistema registra a velocidade de
  operação e a altura de corte. Se a velocidade passa do ideal (padrão 6 km/h) ou o corte de
  base fica alto demais (padrão 5 cm, onde fica a parte mais rica em sacarose), ele gera uma
  recomendação específica.
- **Ranking de colhedoras:** compara as máquinas pela perda média e mostra quantos pontos
  percentuais a pior perde a mais que a melhor, indicando onde revisar regulagem ou
  treinar operador.
- **Painel de indicadores:** perda total, prejuízo acumulado em R$, perda média ponderada por
  tipo de colheita e quantidade de colheitas em cada situação.
- **Modo offline:** se não houver conexão com o Oracle (comum no campo), o sistema continua
  funcionando e salva os dados em JSON, que depois podem ser importados para o banco.

---

## Conteúdos dos capítulos 3 a 6 aplicados

| Conteúdo | Onde está no código |
|---|---|
| **Funções** com passagem de parâmetros e retorno | `calcular_perda()`, `classificar_perda()`, `gerar_recomendacoes()`, `ranking_colhedoras()` em `calculos.py`; leituras validadas em `validacoes.py` |
| **Procedimentos** (sem retorno) com parâmetros | `exibir_cabecalho()`, `exibir_tabela()`, `exibir_detalhes()` em `main.py`; `registrar_log()` em `arquivos.py`; `criar_tabela_se_nao_existir()` em `banco.py` |
| **Lista** | `COLHEITAS` (registros carregados), listas de recomendações e de filtros |
| **Tupla** | `TIPOS_COLHEITA`, `CLASSIFICACOES`, `OPCOES_MENU`, `COLUNAS` do banco, retorno de `calcular_perda()` e itens do ranking |
| **Dicionário** | cada colheita é um dicionário; `ACOES` liga o menu às funções; `config.json` carregado como dicionário |
| **Tabela de memória** | `COLHEITAS`: lista de dicionários com todas as colheitas, sincronizada com o Oracle |
| **Arquivo texto** | `data/relatorio_colheitas.txt` (relatório) e `data/log_operacoes.txt` (histórico de operações) |
| **Arquivo JSON** | `config/config.json` (parâmetros), `data/colheitas_backup.json` (exportar/importar) |
| **Banco Oracle** | `banco.py`: conexão, criação da tabela, INSERT, SELECT, UPDATE e DELETE na `T_COLHEITA_CANA` |

### Consistência das entradas do usuário

Nenhum dado entra no banco sem passar por validação (`validacoes.py`):

- números aceitam vírgula ou ponto e são rejeitados se tiverem letras ou estiverem fora da faixa;
- datas precisam estar no formato DD/MM/AAAA e não podem ser futuras;
- campos obrigatórios não aceitam vazio e têm tamanho máximo compatível com a coluna do banco;
- opções de menu só aceitam os números exibidos;
- toneladas colhidas são limitadas a 150% do esperado, para barrar erro de digitação;
- exclusões e alterações pedem confirmação S/N;
- na importação de JSON, registros incompletos ou duplicados são ignorados e anotados no log.

---

## Estrutura de pastas

```
farmtech-colheita/
├── assets/              # imagens do README (logo da FIAP)
├── config/
│   └── config.json      # preço da tonelada, limites de perda, parâmetros da colhedora, DSN Oracle
├── data/
│   └── colheitas_backup.json   # backup de exemplo com 8 colheitas (para importar na opção 8)
├── document/            # documentos complementares
├── scripts/
│   └── create_table.sql # DDL da tabela T_COLHEITA_CANA (opcional; o programa cria sozinho)
├── src/
│   ├── main.py          # menu e fluxo principal
│   ├── calculos.py      # regras de negócio (perda, classificação, recomendações, ranking)
│   ├── validacoes.py    # leitura e validação das entradas
│   ├── arquivos.py      # arquivos texto e JSON
│   └── banco.py         # conexão e CRUD no Oracle
├── requirements.txt
└── README.md
```

Os arquivos `relatorio_colheitas.txt`, `log_operacoes.txt` e `colheitas_offline.json` são
gerados na pasta `data/` durante o uso.

---

## Como executar o código

**Pré-requisitos:** Python 3.10 ou superior e acesso ao Oracle da FIAP.

1. Instale a dependência:
   ```bash
   pip install -r requirements.txt
   ```
2. (Opcional) Defina usuário e senha do Oracle em variáveis de ambiente. Se não definir, o
   programa pergunta na hora:
   ```bash
   # Windows (PowerShell)
   $env:FARMTECH_DB_USER="RM000000"
   $env:FARMTECH_DB_PASSWORD="sua_senha"

   # Linux / macOS
   export FARMTECH_DB_USER=RM000000
   export FARMTECH_DB_PASSWORD=sua_senha
   ```
3. Execute:
   ```bash
   python src/main.py
   ```
4. Na primeira execução a tabela `T_COLHEITA_CANA` é criada automaticamente. Para popular com
   dados de exemplo, escolha a opção **8 — Importar backup em JSON**.

### Menu

```
[1] Registrar nova colheita
[2] Listar colheitas
[3] Ver detalhes e recomendações de uma colheita
[4] Alterar colheita
[5] Excluir colheita
[6] Painel de indicadores e ranking de colhedoras
[7] Exportar backup em JSON
[8] Importar backup em JSON
[9] Gerar relatório em TXT
[0] Sair
```

### Parâmetros ajustáveis (`config/config.json`)

| Parâmetro | Padrão | Uso |
|---|---|---|
| `preco_tonelada_cana_rs` | 160,00 | converte perda em toneladas para R$ |
| `limites_perda_percentual.MANUAL` | 3% / 5% | até 3% aceitável, até 5% atenção, acima crítica |
| `limites_perda_percentual.MECANIZADA` | 5% / 10% | até 5% aceitável, até 10% atenção, acima crítica |
| `velocidade_max_kmh` | 6,0 | acima disso, recomenda reduzir a velocidade |
| `altura_corte_max_cm` | 5,0 | acima disso, recomenda regular o corte de base |

---

## Referências

- TOTVS. *O que é agronegócio*. Disponível em: https://www.totvs.com/blog/gestao-agricola/o-que-e-agronegocio/
- CHB AGRO. *Perdas na colheita de cana: você sabe como reduzi-las?* Disponível em: https://blog.chbagro.com.br/perdas-na-colheita-de-cana-voce-sabe-como-reduzi-las
- JOSÉ, Jefferson Vieira. *Perdas na colheita mecanizada de cana-de-açúcar*. UNICESUMAR, 2009. Disponível em: https://www.unicesumar.edu.br/epcc-2009/wp-content/uploads/sites/77/2016/07/jefferson_vieira_jose3.pdf
- AEVO. *Agrotech*. Disponível em: https://blog.aevo.com.br/agrotech/
- BOLFE, É. L. et al. *Agricultura digital: pesquisa, desenvolvimento e inovação nas cadeias produtivas*. Embrapa, 2020.

---

## Histórico de lançamentos

* 1.0.0 - 12/10/2026
    * Registro, consulta, alteração e exclusão de colheitas no Oracle
    * Cálculo e classificação de perdas, recomendações e ranking de colhedoras
    * Exportação/importação JSON, relatório TXT e modo offline

## Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/agodoi/template">MODELO GIT FIAP</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">Fiap</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>
