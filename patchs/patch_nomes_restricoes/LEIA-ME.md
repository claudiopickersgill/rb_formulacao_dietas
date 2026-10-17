# Nomes completos nas restrições nutricionais

Substitua somente src/pages/formulation.py pelo arquivo deste pacote e reinicie/republique o app. Faça backup do arquivo antes da troca. O caminho correto é src/pages/formulation.py.

A tabela passa a mostrar nome completo, sigla e unidade: Matéria seca - MS (%), Proteína bruta - PB (%), Cálcio - Ca (%), e assim por diante para todos os nutrientes cadastrados. Os nomes e unidades vêm do registro central do app. A coluna foi ampliada para acomodar as descrições.

Os códigos internos, limites, cálculos e dados do Google Sheets permanecem iguais. Não é necessário renomear colunas na planilha. O editor recebe uma nova chave visual para não reutilizar o estado antigo das abreviações.

Alternativa à cópia: execute git apply --check --ignore-space-change atualizacao.patch e depois git apply --ignore-space-change atualizacao.patch na raiz do projeto. Use somente um método.

Verificações: sintaxe Python e ida/volta entre códigos e rótulos para todos os 23 nutrientes do registro atual. Não houve alteração do projeto original nem da base Google. Para reverter, restaure o arquivo de backup.
