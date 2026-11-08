# NexoFiscal — 15 perguntas técnicas fundamentadas no código

Respostas para preparação de entrevistas de Desenvolvimento Python/Full Stack. Leia as funções antes de declarar que você mesmo as desenhou ou depurou; diferencie sua contribuição, revisão de código e uso de IA/Codex.

## 1. O NexoFiscal emite nota fiscal oficial?
**Não.** O fluxo está em \`demonstracao\`, o provedor é \`simulador\` e os adaptadores nacionais/municipais oficiais lançam \`NotImplementedError\`. Prefixo interno \`SIM-\`, sem autorização de prefeitura. [official.py](../../backend/app/fiscal/adapters/official.py) e [fiscal.md](../fiscal.md).

## 2. Quais tecnologias foram usadas?
React/JSX/Vite, FastAPI/Pydantic, SQLAlchemy/Alembic, SQLite, ReportLab e QR code demonstrativo. PostgreSQL/Compose têm configuração sem nova homologação. [README](../../README.md).

## 3. Qual é a regra essencial de prévia?
Valida cliente e serviço do mesmo escopo, ambos ativos, CPF/CNPJ e ambiente demonstrativo; Pydantic controla competência e montante. [fiscal.py](../../backend/app/services/fiscal.py), [inputs.py](../../backend/app/schemas/inputs.py).

## 4. Por que \`Idempotency-Key\`?
Permite que um POST repetido com mesmo payload retorne a mesma solicitação. Um fingerprint de conteúdo impede reutilizar uma chave com dados distintos. [fiscal.py](../../backend/app/services/fiscal.py). **Estudar:** falhas parciais, conflitos, deduplicação concorrente.

## 5. Como se evitam notas duplicadas por cobrança?
Fluxo de cobrança exige quitação e não ter invoice anterior. Existe restrição única por cobrança. O fluxo avulso não cria cobrança. [fiscal.py](../../backend/app/services/fiscal.py), [entities.py](../../backend/app/models/entities.py).

## 6. O que significa status \`autorizada\`?
É **um estado interno do simulador**, não resposta da prefeitura. A saída gerada tem aviso explícito de inexistência de validade fiscal. [simulator.py](../../backend/app/fiscal/adapters/simulator.py).

## 7. Como é tratada uma rejeição?
O operador pode induzir uma rejeição simulada. O sistema guarda tentativas/eventos; o retry só ocorre em nota rejeitada e revalida condições antes de processar. [fiscal.py](../../backend/app/services/fiscal.py).

## 8. O que acontece ao cancelar?
Somente documento simulado em status autorizado pode ser cancelado por usuário com permissão. Gera eventos de solicitação e cancelamento; segunda tentativa recebe conflito. [business.py](../../backend/app/api/routes/business.py).

## 9. Por que persistir snapshot do documento?
Para preservar dados usados na geração e não reconstruir uma nota histórica apenas a partir de cadastros atuais modificáveis. HTML/PDF/XML derivam do snapshot. [documents.py](../../backend/app/fiscal/documents.py).

## 10. Como são protegidas as sessões?
Cookie HttpOnly com token aleatório cujo hash vai ao banco, CSRF obrigatório nas operações de escrita, papéis \`require(permission)\` e escopo por organização. Cookie Secure depende de configuração: não assumir pronto para hospedagem. [auth.py](../../backend/app/security/auth.py).

## 11. Há risco na conta \`portfolio\`?
Sim. No código atual herda quase todos os privilégios do admin, exceto envio de e-mail; endpoint pode expor senha demo se habilitado. Antes de backend público precisa reduzir permissões, conter mutações e isolar os dados. [auth.py](../../backend/app/security/auth.py), [config.py](../../backend/app/core/config.py).

## 12. O que garante que o PDF é fiscalmente válido?
**Nada:** PDF e XML são **documentos de demonstração**, sem assinatura, certificado, numeração oficial ou autorização. O teste inspeciona prefixo PDF, XML disponível e marca visível no HTML. [documents.py](../../backend/app/fiscal/documents.py).

## 13. Como é feito o envio de e-mail?
Há preparação de .eml e transporte SMTP opcional, com permissão dedicada. Os testes de envio usam transporte simulado, não SMTP real nesta revisão. O perfil portfolio não tem \`email_send\`. [documents_delivery.py](../../backend/app/api/routes/documents_delivery.py).

## 14. O que realmente foi testado?
CI #42533352657: 63 pytest e build Vite aprovados. Três testes novos cobrem idempotência, documentos e estados/permissões. Verificar status separado de Chromium antes de mencionar browser. [EVIDENCIAS.md](EVIDENCIAS.md).

## 15. O que falta para uma integração oficial?
Conector homologado, regras de município/regime, documentos e tributos aplicáveis verificados nas fontes oficiais, certificado/assinatura, tratamento de timeouts e reconciliação com provedor, banco PostgreSQL testado, segurança de produção, LGPD, retry e operação/monitoramento. **Não** inferir conformidade a partir do simulador. [PLANO_DE_MELHORIAS.md](PLANO_DE_MELHORIAS.md).

---

## Exercício para entrevista

Explique, desenhando: \`preview → issue-direct → Invoice/FiscalEvent → documentos\`. Depois demonstre como a mesma chave retorna o mesmo ID e por que a alteração de valor gera 409. Faça o segundo caminho \`rejeitada → retry → autorizada → cancelada\`. Identifique a restrição que impede \`recepcao\` de emitir. Descreva o risco da conta de portfólio com privilégios amplos, mesmo em um sistema demonstrativo.

Nunca afirme que NexoFiscal obteve autorizações oficiais, transmitiu documentos a prefeitura ou produziu resultados comerciais reais.
