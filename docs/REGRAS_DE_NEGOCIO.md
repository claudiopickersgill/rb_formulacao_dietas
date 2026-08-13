# Regras de negócio implementadas

1. A mistura deve totalizar 100%.
2. Inclusões são não negativas.
3. Inclusão mínima não pode superar a máxima.
4. A soma dos mínimos não pode superar 100%.
5. A soma dos máximos deve permitir chegar a 100%.
6. O mesmo `ingredient_id` não pode aparecer duas vezes.
7. Preços devem ser numéricos e não negativos.
8. Cada nutriente pode ter no máximo uma linha de restrição.
9. Limite mínimo não pode superar o máximo.
10. Valor desconhecido deve ficar vazio, não ser registrado como zero.
11. Se uma restrição usa um nutriente ausente em algum ingrediente selecionado, o cálculo é bloqueado.
12. O solver minimiza o custo por kg da mistura.
13. Ingredientes inativos não aparecem em novas seleções, mas continuam disponíveis ao abrir uma dieta histórica.
14. Dietas guardam a composição nutricional utilizada no momento do cálculo.
15. Administradores veem todas as dietas; demais perfis veem as próprias.
16. Somente Administrador e Formulador podem persistir alterações.
17. Exclusão de dieta remove seus ingredientes e restrições relacionados.
18. Operações relevantes geram registros de auditoria.
