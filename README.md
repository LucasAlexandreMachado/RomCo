# RomCo 🎮

Um poderoso e elegante gerenciador de coleções de ROMs (jogos retrô). O objetivo do **RomCo** é facilitar a organização de enormes coleções de jogos, automatizando tarefas repetitivas como extrair arquivos zip, renomear ROMs, mover para pastas específicas e comparar arquivos com bancos de dados de hashes (ex: No-Intro).

## 🛠️ Tecnologias Utilizadas
- **Backend**: Python 3
- **Desktop Framework**: PyWebView (com PyQt6 / QtWebEngine) para criar uma janela nativa extremamente leve sem a barra de ferramentas do navegador.
- **Frontend**: HTML5, CSS3 puro e Vanilla JavaScript.
- **Ícones**: Lucide Icons.
- **Design Base**: O layout visual foi portado com base no _Romie Design Spec_.

## 🚀 Como Executar

1. Certifique-se de estar dentro da pasta raiz do projeto.
2. Ative o ambiente virtual:
   ```bash
   source venv/bin/activate
   ```
3. Execute o script principal do Python:
   ```bash
   python main.py
   ```

A interface visual abrirá automaticamente usando as bibliotecas gráficas nativas do seu sistema operacional.

## 🗺️ Roadmap e Funcionalidades

O projeto está sendo construído em módulos. Aqui está o progresso:

- [x] **Fase 1: Estrutura Visual e Arquitetura**
  - Criação do layout em 3 colunas (Sidebar, Lista, Detalhes).
  - Setup do Python e integração com Frontend assíncrono via `PyWebView`.
- [x] **Fase 2: Módulo Scanner**
  - Fazer a varredura real nos diretórios locais do usuário.
  - Carregar arquivos `.zip`, `.nes`, `.smd` etc e mostrar na interface visual.
- [ ] **Fase 3: Módulo Archiver / Renamer**
  - Renomear arquivos em lote, removendo "tags" sujas de nomes.
  - Zipar e deszipar ROMs soltas.
- [ ] **Fase 4: Módulo Organizer (Mover pastas)**
  - Organizar arquivos estruturalmente (ex: mover arquivos com a letra "A" para a pasta `/A`).
- [ ] **Fase 5: Módulo Verifier (Avançado)**
  - Comparar hashes CRC32 com arquivos `.DAT` do sistema No-Intro/Redump.

---
> **Nota de desenvolvimento**: Este README será constantemente atualizado conforme novas instruções e módulos forem definidos.
