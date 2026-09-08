<!--
  Preencha todas as seções antes de pedir revisão.
  PRs sem este template preenchido podem ser fechados sem revisão.
-->

## Descrição da mudança

<!-- O que mudou e por quê. Evite apenas "fix bug" — descreva a causa raiz. -->



## Origem da mudança

- [ ] Autoria humana
- [ ] Autoria de agente autônomo — **qual agente:** ____________________
      **tarefa/prompt que originou esta mudança:** ____________________

## Tipo de mudança

- [ ] Correção de bug
- [ ] Nova funcionalidade
- [ ] Refatoração (sem mudança de comportamento)
- [ ] Alteração de configuração / infraestrutura
- [ ] Atualização de dependência

## Issue relacionada

Closes #____

## Como foi validado

<!-- "Rodei local e pareceu ok" não é validação suficiente para mudanças geradas por agente. -->

- [ ] Testes automatizados novos ou atualizados cobrindo esta mudança
- [ ] Suite de testes existente rodou e passou (CI verde)
- [ ] Testado manualmente — descreva o cenário: ____________________
- [ ] N/A — justifique por que nenhuma validação acima se aplica: ____________________

## Checklist antes de pedir revisão

- [ ] Nenhum segredo, chave de API ou credencial no diff
- [ ] Esta mudança não altera o contrato (input/output) de uma função ou API consumida por outro agente sem sinalizar abaixo
- [ ] Documentação/README atualizados, se o comportamento mudou
- [ ] O diff foi revisado por mim mesmo linha a linha antes de abrir o PR

## Risco e plano de rollback

<!-- Se isso quebrar algo em produção, o que fazemos? -->

**Risco (baixo / médio / alto):**

**Como reverter, se necessário:**

## Revisor(es) necessário(s)

<!-- Marque o CODEOWNER da área afetada. Nenhum PR deve ser aprovado pelo próprio autor. -->

@____________________
