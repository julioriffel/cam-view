# 👁️ Análise e Revisão da Estratégia de Detecção de Movimento no CamView

Este documento apresenta uma revisão técnica detalhada do mecanismo atual de detecção e rastreamento de movimento do **CamView**, diagnostica suas forças e limitações, e propõe um catálogo abrangente de estratégias alternativas — desde métodos computacionais ultraleves até arquiteturas modernas de visão computacional e integração com hardware.

---

## 📌 Sumário
1. [Diagnóstico da Estratégia Atual](#1-diagnóstico-da-estratégia-atual)
2. [Pontos Fortes do Mecanismo Atual](#2-pontos-fortes-do-mecanismo-atual)
3. [Limitações e Gargalos Identificados](#3-limitações-e-gargalos-identificados)
4. [Catálogo de Estratégias Alternativas](#4-catálogo-de-estratégias-alternativas)
   - [Alternativa 1: MOG2 Otimizado com Downscaling e ROIs](#alternativa-1-mog2-otimizado-com-downscaling-e-rois)
   - [Alternativa 2: Subtração de Fundo via KNN (K-Nearest Neighbors)](#alternativa-2-subtração-de-fundo-via-knn-k-nearest-neighbors)
   - [Alternativa 3: Diferenciação Temporal de 3 Quadros (Three-Frame Differencing)](#alternativa-3-diferenciação-temporal-de-3-quadros-three-frame-differencing)
   - [Alternativa 4: Fluxo Óptico (Optical Flow) e Linhas Virtuais (Tripwires)](#alternativa-4-fluxo-óptico-optical-flow-e-linhas-virtuais-tripwires)
   - [Alternativa 5: Pipeline AI-First Contínuo com Frame-Skipping](#alternativa-5-pipeline-ai-first-contínuo-com-frame-skipping)
   - [Alternativa 6: Extração de Vetores de Movimento H.264/H.265 (Motion Vectors)](#alternativa-6-extração-de-vetores-de-movimento-h264h265-motion-vectors)
   - [Alternativa 7: Integração Direta com Eventos ONVIF / API Intelbras MHDX](#alternativa-7-integração-direta-com-eventos-onvif--api-intelbras-mhdx)
5. [Matriz Comparativa de Tecnologias](#5-matriz-comparativa-de-tecnologias)
6. [Arquitetura Recomendada para o CamView](#6-arquitetura-recomendada-para-o-camview)
7. [Exemplos SPráticos de Implementação](#7-exemplos-práticos-de-implementação)

---

## 1. Diagnóstico da Estratégia Atual

Atualmente, o CamView emprega uma **arquitetura híbrida em cascata (Two-Stage Pipeline)** implementada no módulo [`src/core/stream_worker.py`](file:///home/julio/projects/cam-wiew/src/core/stream_worker.py) e integrada com o [`src/core/ai_detector.py`](file:///home/julio/projects/cam-wiew/src/core/ai_detector.py):

```
┌──────────────┐     ┌────────────────┐     ┌───────────────────────┐
│ RTSP Stream  │ ──► │  MOG2 (OpenCV) │ ──► │ Filtro Morfológico    │
│ Frame BGR    │     │  Subtração     │     │ (cv2.MORPH_OPEN 5x5)  │
└──────────────┘     └────────────────┘     └───────────┬───────────┘
                                                        │
┌──────────────────────────────┐                        ▼
│  Classificação e Alerta      │            ┌───────────────────────┐
│  • Bounding Boxes coloridas  │ ◄───────── │ Extração de Contornos │
│  • Snapshot & SQLite DB      │  (Se Pers. │ Área Mínima (ex: 1500)│
│  • YOLOv5n ONNX (se AI ativa)│  >= N)     │ Persistência Temporal │
└──────────────────────────────┘            └───────────────────────┘
```

### Passo a passo do fluxo em tempo real:
1. **Subtração de Fundo (MOG2)**: Instância de `cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)`.
2. **Warm-up / Treinamento**: 30 frames iniciais descartados para estabilização do modelo estático.
3. **Limpeza Morfológica**: Aplicação opcional de abertura morfológica (`cv2.morphologyEx` com kernel elíptico 5x5) para filtrar ruídos pontuais (insetos voando, pingos de chuva).
4. **Segmentação e Área**: Busca de contornos externos (`cv2.findContours`) e descarte de áreas inferiores a `tracking_min_area` (padrão: 1500 px²).
5. **Filtro de Persistência Temporal**: Requer `consecutive_motion_frames >= tracking_persistence` (padrão: 5 frames) para confirmar que o movimento não é uma oscilação instantânea de iluminação.
6. **Validação por Inteligência Artificial (Cascata)**:
   - Se o Smart Vision (AI) estiver ativado, o frame completo é enviado ao `AIDetector` (YOLOv5n ONNX rodando em CPU).
   - O detector verifica se há **Pessoas**, **Veículos** ou **Animais**.
   - Se confirmado, salva snapshots com debounce, emite alertas desktop e registra no banco SQLite (`events.db`).
   - Se não houver alvo de IA reconhecido, desenha apenas retângulos verdes nos contornos de movimento detectados pelo MOG2.

---

## 2. Pontos Fortes do Mecanismo Atual

* **Eficiência Energética e de CPU**: Ao utilizar o MOG2 como filtro primário, a rede neural pesada (YOLO) só roda quando há movimento real na cena, economizando ciclos de CPU em 90% do tempo.
* **Modelo Adaptativo a Luz Lenta**: O MOG2 com histórico de 500 frames ajusta-se naturalmente às mudanças graduais de luz do sol ao longo do dia.
* **Redução de Falsos Positivos via Persistência**: A exigência de N frames consecutivos de movimento impede alarmes falsos causados por quedas pontuais de compressão ou artefatos de codec RTSP.
* **Zero Dependências Pesadas**: A inferência do modelo ONNX é executada pelo runtime nativo `cv2.dnn`, sem necessidade de pacotes massivos como PyTorch, TensorFlow ou CUDA instalados no sistema operacional.

---

## 3. Limitações e Gargalos Identificados

Apesar de funcional, a análise do código e dos testes práticos revela alguns pontos de atrito:

1. **Processamento em Resolução Máxima (Gargalo de CPU)**:
   - O MOG2 e a busca de contornos operam diretamente na resolução nativa do frame (por exemplo, 1080p ou 2K). Isso consome muito mais CPU e memória do que o necessário para detectar movimento macro.
2. **Inércia / Efeito Fantasma (Ghosting) do MOG2**:
   - Se um carro estacionar na cena ou uma pessoa parar para conversar, o MOG2 gradualmente a incorpora ao fundo após alguns segundos (`history=500`), fazendo o contorno sumir mesmo com o objeto ainda presente.
3. **Ausência de Zonas de Máscara (ROI - Region of Interest)**:
   - O algoritmo analisa o quadro inteiro. Folhagens de árvores balançando ao vento, bandeiras, relógios/timestamps embutidos da câmera e tráfego em vias públicas no fundo geram disparos contínuos.
4. **Execução Síncrona na Thread do Stream**:
   - A inferência do YOLOv5n é chamada no mesmo laço de leitura do RTSP (`StreamWorker.run()`). Em CPUs com menor clock, uma inferência que leve ~80-150ms pode causar congelamento momentâneo ou descarte de frames no buffer do stream de vídeo da UI.
5. **Sombras e Variações Globais de Iluminação**:
   - Com `detectShadows=False`, sombras de carros ou nuvens projetadas no chão são interpretadas como objetos sólidos em movimento, alterando a caixa delimitadora e acionando disparos indevidos.

---

## 4. Catálogo de Estratégias Alternativas

Abaixo estão descritas alternativas viáveis, com diferentes balanços entre custo de processamento, precisão e facilidade de implementação.

---

### Alternativa 1: MOG2 Otimizado com Downscaling e ROIs

**Conceito**: Manter o algoritmo MOG2 atual, mas otimizar radicalmente a entrada através de redução de escala (downscaling) e suporte a máscaras poligonais de inclusão/exclusão.

* **Como Funciona**:
  1. Reduz o frame temporariamente para resolução baixa (ex: 360p ou largura de 480px).
  2. Aplica uma máscara binária (ROI) descartando áreas indesejadas (árvores, calçada pública, carimbo de data/hora).
  3. Roda o MOG2 e contornos no frame reduzido.
  4. Redimensiona as coordenadas dos contornos de volta para a escala original do vídeo.
* **Vantagens**:
  - Redução de até **70% do uso de CPU** no processamento do MOG2.
  - Elimina falsos positivos causados por áreas periféricas com vento ou tráfego irrelevante.
* **Desvantagens**:
  - Objetos muito distantes (poucos pixels) podem se perder na redução de escala.

---

### Alternativa 2: Subtração de Fundo via KNN (K-Nearest Neighbors)

**Conceito**: Substituir o `cv2.createBackgroundSubtractorMOG2` por `cv2.createBackgroundSubtractorKNN(history=400, dist2Threshold=400.0, detectShadows=True)`.

* **Como Funciona**:
  - O algoritmo KNN modela cada pixel através dos vizinhos mais próximos no tempo.
  - Possui um discriminador nativo de sombras mais eficiente que o MOG2, marcando sombras como cinza (`127`) e movimento real como branco (`255`).
* **Vantagens**:
  - Melhor adaptação a cenas com fundos dinâmicos complexos (superfície de piscinas, grama oscilante).
  - Capacidade superior de ignorar sombras projetadas.
* **Desvantagens**:
  - Ligeiramente mais intensivo em memória que o MOG2 simples.

---

### Alternativa 3: Diferenciação Temporal de 3 Quadros (Three-Frame Differencing)

**Conceito**: Técnica clássica ultraleve que compara a diferença absoluta entre três quadros consecutivos ($Frame_{t-2}$, $Frame_{t-1}$ e $Frame_t$).

* **Como Funciona**:
  ```python
  d1 = cv2.absdiff(frame_t_minus_1, frame_t_minus_2)
  d2 = cv2.absdiff(frame_t, frame_t_minus_1)
  motion_mask = cv2.bitwise_and(d1, d2)
  _, thresh = cv2.threshold(motion_mask, 25, 255, cv2.THRESH_BINARY)
  ```
* **Vantagens**:
  - **Uso de CPU praticamente nulo** (operações aritméticas diretas em matrizes NumPy).
  - Sem necessidade de aprendizado ou histórico de fundo (não há tempo de warm-up).
  - Imune ao problema de objetos estacionários serem incorporados ao fundo como fantasmas.
* **Desvantagens**:
  - Não preenche o corpo do objeto completamente (apenas detecta as bordas em movimento).
  - Se o objeto se mover muito devagar ou parar completamente, a detecção cessa de imediato.

---

### Alternativa 4: Fluxo Óptico (Optical Flow) e Linhas Virtuais (Tripwires)

**Conceito**: Em vez de apenas identificar se há pixels mudando, o Fluxo Óptico (ex: Farnebäck denso ou Lucas-Kanade esparso) calcula o **vetor de velocidade e direção** $(dx, dy)$ de cada ponto.

* **Como Funciona**:
  1. Identifica pontos de interesse com `cv2.goodFeaturesToTrack` ou MOG2.
  2. Rastreia os pontos no frame seguinte usando `cv2.calcOpticalFlowPyrLK`.
  3. Calcula o vetor de deslocamento.
  4. Permite configurar **Linhas Virtuais de Passagem (Tripwires)**: dispara alarme apenas se um objeto cruzar a linha em uma direção específica (ex: entrando na garagem, mas não saindo).
* **Vantagens**:
  - Discrimina direção de movimento (evita alertas em direções não prioritárias).
  - Consegue diferenciar movimento global (câmera tremendo ao vento) de movimento local de objetos.
* **Desvantagens**:
  - Custo de processamento mais elevado. Recomenda-se aplicar de forma esparsa apenas dentro de caixas delimitadoras de interesse.

---

### Alternativa 5: Pipeline AI-First Contínuo com Frame-Skipping

**Conceito**: Eliminar completamente os algoritmos de subtração de fundo tradicionais e rodar a detecção de objetos por Redes Neurais (YOLOv8n / YOLOv11n / MobileNet-SSD) diretamente no fluxo de vídeo, em frequência controlada.

* **Como Funciona**:
  - A IA não é executada a cada frame (20-30 FPS), mas sim a **3 a 5 FPS** em uma thread separada dedicada.
  - Os quadros intermediários são interpolados através de um rastreador leve (como ByteTrack, SORT ou Lucas-Kanade).
* **Vantagens**:
  - **Precisão máxima absoluta**: total imunidade a folhas de árvores, sombras, chuva, neblina e reflexos de farol.
  - Reconhece uma pessoa ou veículo mesmo que estejam 100% parados há horas.
* **Desvantagens**:
  - Carga constante de CPU/GPU (embora a 3 FPS com modelos nano modernos seja perfeitamente suportável em computadores convencionais).

---

### Alternativa 6: Extração de Vetores de Movimento H.264/H.265 (Motion Vectors)

**Conceito**: Os codecs de compressão de vídeo (H.264 e H.265) já calculam internamente os vetores de movimento dos macro-blocos para comprimir o fluxo RTSP enviado pela câmera.

* **Como Funciona**:
  - Através de bindings do FFmpeg (ex: `PyAV` com `export_mvs=True`), lê-se os vetores de movimento brutos diretamente dos pacotes comprimidos durante a demultiplexação.
* **Vantagens**:
  - **Uso de CPU zero para detecção**: não é necessário decodificar nem processar a imagem com filtros gráficos.
* **Desvantagens**:
  - Requer manipulação avançada de streams via libavcodec / PyAV em vez do `cv2.VideoCapture` padrão.
  - Resolução espacial granular (baseada em blocos de 8x8 ou 16x16 pixels).

---

### Alternativa 7: Integração Direta com Eventos ONVIF / API Intelbras MHDX

**Conceito**: Os DVRs Intelbras MHDX e câmeras IP modernas já possuem processadores DSP integrados dedicados à detecção de movimento e inteligência artificial perimetral (linhas e cercas virtuais).

* **Como Funciona**:
  - O CamView conecta-se ao serviço de eventos do DVR via protocolo ONVIF (WS-Notification) ou escuta o stream de eventos HTTP da API Dahua/Intelbras (`/cgi-bin/eventManager.cgi?action=attach&codes=[VideoMotion,CrossLineDetection]`).
  - O DVR envia eventos instantâneos via push quando o movimento ocorre em qualquer canal.
* **Vantagens**:
  - **Zero processamento no computador cliente**: o hardware do DVR assume 100% da carga de análise.
  - Máxima confiabilidade e sincronia com as gravações nativas do próprio DVR.
* **Desvantagens**:
  - Depende dos recursos suportados pelo firmware de cada modelo de DVR.

---

## 5. Matriz Comparativa de Tecnologias

| Estratégia | Custo de CPU | Precisão Contra Falsos Positivos | Detecção de Objetos Parados | Suporte a Direção / Sentido | Complexidade de Implementação |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **MOG2 Atual (Original)** | Médio | Média (sujeito a sombras e vento) | Baixa (efeito fantasma) | Não | ⭐ Baixa (Já existe) |
| **MOG2 Otimizado + ROI + Downscale** | 🟢 Muito Baixo | Boa (com exclusão de zonas) | Baixa | Não | ⭐ Baixa |
| **KNN com Detecção de Sombras** | Baixo | Boa (filtra sombras) | Baixa | Não | ⭐ Baixa |
| **3-Frame Differencing** | 🟢 Quase Nulo | Baixa | ❌ Nula | Não | ⭐ Baixa |
| **Fluxo Óptico (Optical Flow)** | Médio-Alto | Alta | Média |  Sim (Vetores X, Y) | ⭐⭐⭐ Média |
| **AI-First (YOLO Contínuo a 3-5 FPS)** | Médio | 🟢 Excelente | 🟢 Excelente | Via Rastreamento (Tracker) | ⭐⭐ Média |
| **H.264 Motion Vectors** | 🟢 Zero | Média | Baixa | Sim | ⭐⭐⭐⭐ Alta |
| **Eventos Nativos ONVIF/Intelbras** | 🟢 Zero | Conforme Configuração do DVR | Conforme DVR | Conforme DVR | ⭐⭐⭐ Média |

---

## 6. Arquitetura Recomendada para o CamView

A solução mais robusta, modular e de alto desempenho para o CamView consiste em uma **Estratégia Híbrida Desacoplada de 3 Fases**:

```
                       CÂMERA RTSP STREAM
                              │
                ┌─────────────┴─────────────┐
                ▼                           ▼
        [Thread de Vídeo]           [Fila Assíncrona]
        • Exibição contínua         • Downscaling (480p)
        • 20-30 FPS sem lag         • Máscaras de Zona (ROI)
                │                           │
                │                           ▼
                │                  [Detector Leve: KNN/MOG2]
                │                           │
                │                  (Movimento persistente?)
                │                           │ SIM
                │                           ▼
                │                  [Worker de IA Assíncrono]
                │                  • YOLOv5n / YOLOv8n ONNX
                │                  • Pessoas, Veículos, Pets
                │                           │
                │                           ▼
                └────────────────── [Alertas & Snapshots]
                                    • Notificação Desktop
                                    • Gravação em SQLite
```

### Pilares da Recomendação:
1. **Desacoplamento em Threads (Producer-Consumer)**:
   - A captura do RTSP nunca espera o processamento de imagem ou inferência de IA. Isso elimina qualquer gaguejo (*stuttering*) ou acúmulo de buffer na tela.
2. **Processamento em Escala Reduzida (Downscaled Processing)**:
   - Toda análise de subtração de fundo deve rodar em um quadro redimensionado (ex: largura fixa de 480px ou 640px). As caixas resultantes são mapeadas de volta às dimensões reais apenas para desenho na tela.
3. **Editor de Zonas de Interesse (ROI Masks)**:
   - Permitir ao usuário pintar ou desenhar polígonos nas configurações para ignorar copas de árvores, fios com passarinhos ou a rua ao fundo.
4. **Validação Inteligente por IA Sob Demanda**:
   - Manter a cascata atual, mas tornando a chamada do YOLO não-bloqueante.

---

## 7. Exemplos Práticos de Implementação

### Exemplo A: Downscaling Eficiente e Máscara ROI para Subtração de Fundo

```python
import cv2
import numpy as np

class OptimizedMotionDetector:
    def __init__(self, target_width: int = 480, min_area: int = 400):
        self.target_width = target_width
        self.min_area = min_area
        self.bg_subtractor = cv2.createBackgroundSubtractorKNN(
            history=400, dist2Threshold=400.0, detectShadows=True
        )
        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self.roi_mask = None

    def set_roi_polygon(self, frame_shape: tuple, polygon_points: list[tuple[int, int]]):
        """Define uma máscara poligonal de interesse (inclusão)."""
        h, w = frame_shape[:2]
        self.roi_mask = np.zeros((h, w), dtype=np.uint8)
        pts = np.array(polygon_points, dtype=np.int32)
        cv2.fillPoly(self.roi_mask, [pts], 255)

    def process_frame(self, frame: np.ndarray) -> tuple[bool, list[tuple[int, int, int, int]]]:
        orig_h, orig_w = frame.shape[:2]
        scale = self.target_width / float(orig_w)
        target_h = int(orig_h * scale)

        # 1. Redução de escala rápida para economizar CPU
        small_frame = cv2.resize(frame, (self.target_width, target_h), interpolation=cv2.INTER_LINEAR)

        # 2. Subtração de fundo
        fg_mask = self.bg_subtractor.apply(small_frame)

        # 3. Remover sombras (KNN marca sombras com valor 127)
        _, fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)

        # 4. Aplicação de ROI se configurada
        if self.roi_mask is not None:
            small_roi = cv2.resize(self.roi_mask, (self.target_width, target_h), interpolation=cv2.INTER_NEAREST)
            fg_mask = cv2.bitwise_and(fg_mask, small_roi)

        # 5. Filtragem morfológica de ruído
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self.kernel)

        # 6. Detecção de contornos
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        boxes = []
        inv_scale = 1.0 / scale
        for cnt in contours:
            if cv2.contourArea(cnt) > self.min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                # Reescalar as coordenadas para o tamanho original do vídeo
                boxes.append((
                    int(x * inv_scale),
                    int(y * inv_scale),
                    int(w * inv_scale),
                    int(h * inv_scale)
                ))

        has_motion = len(boxes) > 0
        return has_motion, boxes
```

---

### Exemplo B: Rastreamento de Passagem por Linha Virtual (Tripwire)

```python
def check_line_crossing(prev_center: tuple[int, int], curr_center: tuple[int, int], line: tuple[tuple[int, int], tuple[int, int]]) -> bool:
    """Verifica se o vetor de deslocamento de um objeto cruzou uma linha virtual."""
    (x1, y1), (x2, y2) = line
    (px, py), (cx, cy) = prev_center, curr_center

    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) > (b[1] - a[1]) * (c[0] - a[0])

    # Interseção de segmentos de reta
    return ccw((px, py), (x1, y1), (x2, y2)) != ccw((cx, cy), (x1, y1), (x2, y2)) and \
           ccw((px, py), (cx, cy), (x1, y1)) != ccw((px, py), (cx, cy), (x2, y2))
```

---

## 🎯 Conclusão

A estratégia atual do CamView (MOG2 + YOLOv5n ONNX) possui uma excelente base conceitual, pois economiza energia executando a rede neural apenas sob demanda. 

As melhorias com maior retorno imediato de qualidade e desempenho são:
1. **Downscaling do frame** antes do MOG2/KNN (ganho imediato de performance na CPU).
2. **Substituição por KNN com eliminação de sombras** para evitar disparos com luz solar/nuvens.
3. **Inclusão de Zonas de Interesse (ROI)** na interface para que o usuário delimite onde quer monitorar.
4. **Desacoplamento assíncrono da inferência de IA**, prevenindo qualquer travamento perceptível na renderização do vídeo.
