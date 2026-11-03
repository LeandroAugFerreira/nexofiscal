# Fiscal — somente simulação

A emissão avulsa simulada foi acrescentada como fluxo principal para clientes PF/PJ de prestadores de serviços. Ela valida cliente e serviço ativos e o ambiente demonstrativo, persiste documento/eventos e não cria registros financeiros. A emissão vinculada a cobrança mantém exigência de quitação e unicidade por cobrança. Consulte `central-emissao.md` para a jornada atual; as regras abaixo continuam aplicáveis ao fluxo por cobrança e à arquitetura do simulador.

Adaptador funcional: `SimuladorFiscalAdapter`. `FiscalAdapter` define `emitir_nota`, `consultar_nota`, `cancelar_nota`, `obter_documento`, `verificar_conexao`. `NfseNacionalAdapter` e `NfseMunicipalAdapter` são contratos de evolução bloqueados; operações reais lançam `NotImplementedError`.

Ambiente único: Demonstração. Configuração API só aceita provedor `simulador` e ambiente `demonstracao`; editar o banco para outro ambiente também bloqueia a emissão. Não há endpoints governamentais, número oficial, código de verificação, certificados, regras tributárias ou autorização de prefeitura na aplicação.

Estados implementados: aguardando emissão → processando → autorizada ou rejeitada; rejeitada → processando → autorizada; autorizada → cancelamento solicitado → cancelada. São estados internos simulados. Rascunho existe no vocabulário futuro, mas não há editor de rascunho na v0.1. Lotes possuem somente tabelas reservadas.

Quitação integral, aluno ativo, ambiente correto e ausência de nota prévia são requisitos. Registro persistente, restrição única por cobrança e chave de operação impedem duplicações. Tentativas/eventos preservados; resultado é consultado antes de reprocessar. SQLite tem testes concorrentes; PostgreSQL usa bloqueio de linha e deve ser validado em runtime antes de implantação. Num adaptador real, um timeout nunca deve ser tratado automaticamente como rejeição: será necessário reconciliar com o provedor.

Identificador interno: `SIM-AAAA-NNNNNN`. Documento HTML persistido, com escape de entradas, marca explícita **DOCUMENTO SIMULADO — SEM VALIDADE FISCAL** e CSP sem scripts. Não há PDF oficial ou DANFSe. Dados fiscais de serviços são referência textual sem efeito tributário.

Documentação oficial será exigida antes de qualquer emissão real, incluindo município/provedor aplicável, regime, cadastro do contribuinte, códigos de serviço e exigências vigentes de Reforma Tributária. Fontes usadas para a fundação técnica: [FastAPI — Security](https://fastapi.tiangolo.com/tutorial/security/), [SQLAlchemy — Constraints](https://docs.sqlalchemy.org/en/20/core/constraints.html), [n8n — Docker](https://docs.n8n.io/hosting/installation/docker/). Nenhuma regra fiscal foi inferida dessas fontes.
