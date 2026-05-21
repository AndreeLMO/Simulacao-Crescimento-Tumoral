"""
===========================================================
SIMULAÇÃO AVANÇADA DE CRESCIMENTO TUMORAL
MODELO PDE + AUTÔMATO CELULAR
===========================================================

NOVA IMPLEMENTAÇÃO:
-------------------
Difusão REAL usando Equações Diferenciais Parciais (PDE)

Equação de Difusão-Reação:

dO/dt = D∇²O - kC

Onde:
- O = oxigênio
- D = coeficiente de difusão
- C = consumo celular

O modelo agora possui:
- PDE de oxigênio
- crescimento tumoral
- necrose
- hipóxia
- angiogênese
- quimioterapia
- radioterapia
- clones agressivos
- quiescência
- IA preditiva

BIBLIOTECAS:
-------------
pip install numpy matplotlib scipy scikit-learn pillow

AUTOR:
-------
André Luiz
"""

# =========================================================
# IMPORTAÇÃO DAS BIBLIOTECAS
# =========================================================

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl

from matplotlib.animation import (
    FuncAnimation,
    PillowWriter
)

from matplotlib.colors import ListedColormap

from sklearn.linear_model import LinearRegression


# =========================================================
# CONFIGURAÇÕES
# =========================================================

mpl.rcParams['animation.embed_limit'] = 50

plt.rcParams["figure.figsize"] = (16, 10)


# =========================================================
# REPRESENTAÇÃO CELULAR
# =========================================================

VAZIO = 0
TUMOR = 1
NECROSE = 2
VASO = 3
AGRESSIVO = 4
QUIESCENTE = 5


# =========================================================
# PARÂMETROS
# =========================================================

grid_size = 120

# Crescimento
growth_probability = 0.12
aggressive_growth = 0.25

# PDE Oxigênio
D_oxygen = 0.15
oxygen_consumption = 0.02
dt = 0.1

# Limiares
necrosis_threshold = 0.10
quiescent_threshold = 0.25
proliferation_threshold = 0.45

# Mutação
mutation_probability = 0.001

# Migração
migration_probability = 0.03

# Quimioterapia
drug_decay = 0.01
drug_kill_probability = 0.20

# Radioterapia
radiotherapy_probability = 0.15

# Tratamentos
chemotherapy_start = 80
radiotherapy_start = 120


# =========================================================
# MATRIZES
# =========================================================

grid = np.zeros((grid_size, grid_size))

oxygen = np.ones((grid_size, grid_size))

drug = np.zeros((grid_size, grid_size))


# =========================================================
# TUMOR INICIAL
# =========================================================

center = grid_size // 2

grid[center, center] = TUMOR


# =========================================================
# CORES
# =========================================================

cmap = ListedColormap([
    'black',
    'red',
    'yellow',
    'blue',
    'magenta',
    'green'
])


# =========================================================
# HISTÓRICOS
# =========================================================

tumor_history = []
aggressive_history = []
necrosis_history = []
oxygen_history = []
time_history = []


# =========================================================
# FIGURA
# =========================================================

fig = plt.figure(figsize=(16, 10))

ax1 = plt.subplot(2, 2, 1)
ax2 = plt.subplot(2, 2, 2)
ax3 = plt.subplot(2, 2, 3)
ax4 = plt.subplot(2, 2, 4)


# =========================================================
# PDE DE DIFUSÃO DE OXIGÊNIO
# =========================================================

def diffuse_oxygen_pde():

    global oxygen

    new_oxygen = oxygen.copy()

    # --------------------------------------------
    # EQUAÇÃO PDE
    # --------------------------------------------

    for x in range(1, grid_size - 1):

        for y in range(1, grid_size - 1):

            # Laplaciano discreto

            laplacian = (

                oxygen[x+1, y]
                +
                oxygen[x-1, y]
                +
                oxygen[x, y+1]
                +
                oxygen[x, y-1]
                -
                4 * oxygen[x, y]

            )

            # Consumo tumoral

            consumption = 0

            if (
                grid[x, y] == TUMOR
                or
                grid[x, y] == AGRESSIVO
                or
                grid[x, y] == QUIESCENTE
            ):

                consumption = oxygen_consumption

            # PDE

            diffusion = D_oxygen * laplacian

            reaction = -consumption

            new_oxygen[x, y] = (

                oxygen[x, y]
                +
                dt * (
                    diffusion
                    +
                    reaction
                )
            )

    # --------------------------------------------
    # CONDIÇÕES DE CONTORNO
    # --------------------------------------------

    new_oxygen[0, :] = 1.0
    new_oxygen[-1, :] = 1.0

    new_oxygen[:, 0] = 1.0
    new_oxygen[:, -1] = 1.0

    # Vasos aumentam oxigênio

    vessels = np.argwhere(grid == VASO)

    for x, y in vessels:

        new_oxygen[x, y] = 1.0

    oxygen[:] = np.clip(new_oxygen, 0, 1)


# =========================================================
# DIFUSÃO DE DROGA
# =========================================================

def diffuse_drug():

    global drug

    new_drug = drug.copy()

    for x in range(1, grid_size - 1):

        for y in range(1, grid_size - 1):

            laplacian = (

                drug[x+1, y]
                +
                drug[x-1, y]
                +
                drug[x, y+1]
                +
                drug[x, y-1]
                -
                4 * drug[x, y]

            )

            new_drug[x, y] = (

                drug[x, y]
                +
                0.1 * laplacian
                -
                drug_decay
            )

    # Entrada pelas bordas

    new_drug[0, :] = 1.0
    new_drug[-1, :] = 1.0

    new_drug[:, 0] = 1.0
    new_drug[:, -1] = 1.0

    drug[:] = np.clip(new_drug, 0, 1)


# =========================================================
# ANGIOGÊNESE
# =========================================================

def angiogenesis():

    hypoxic = np.argwhere(

        (
            (grid == TUMOR)
            |
            (grid == AGRESSIVO)
        )
        &
        (oxygen < 0.20)
    )

    for x, y in hypoxic:

        neighbors = [

            (x + dx, y + dy)

            for dx in [-1, 0, 1]
            for dy in [-1, 0, 1]

            if (
                (dx != 0 or dy != 0)
                and
                (0 <= x + dx < grid_size)
                and
                (0 <= y + dy < grid_size)
            )
        ]

        for nx, ny in neighbors:

            if grid[nx, ny] == VAZIO:

                if np.random.random() < 0.015:

                    grid[nx, ny] = VASO


# =========================================================
# QUIMIOTERAPIA
# =========================================================

def apply_chemotherapy():

    tumor_cells = np.argwhere(

        (
            (grid == TUMOR)
            |
            (grid == AGRESSIVO)
            |
            (grid == QUIESCENTE)
        )
    )

    for x, y in tumor_cells:

        resistance = 0

        if grid[x, y] == AGRESSIVO:

            resistance = 0.6

        if grid[x, y] == QUIESCENTE:

            resistance = 0.8

        probability = (
            drug_kill_probability
            *
            drug[x, y]
            *
            (1 - resistance)
        )

        if np.random.random() < probability:

            grid[x, y] = NECROSE


# =========================================================
# RADIOTERAPIA
# =========================================================

def apply_radiotherapy():

    tumor_cells = np.argwhere(

        (
            (grid == TUMOR)
            |
            (grid == AGRESSIVO)
        )
    )

    for x, y in tumor_cells:

        if oxygen[x, y] > 0.3:

            resistance = 0

            if grid[x, y] == AGRESSIVO:

                resistance = 0.5

            probability = (
                radiotherapy_probability
                *
                (1 - resistance)
            )

            if np.random.random() < probability:

                grid[x, y] = NECROSE


# =========================================================
# IA
# =========================================================

def train_ai():

    if len(tumor_history) < 20:

        return None

    X = np.array(time_history).reshape(-1, 1)

    y = np.array(tumor_history)

    model = LinearRegression()

    model.fit(X, y)

    return model


# =========================================================
# UPDATE
# =========================================================

def update(frame):

    global grid

    # -----------------------------------------------------
    # PDE OXIGÊNIO
    # -----------------------------------------------------

    diffuse_oxygen_pde()

    # -----------------------------------------------------
    # DROGA
    # -----------------------------------------------------

    if frame > chemotherapy_start:

        diffuse_drug()

    # -----------------------------------------------------
    # ANGIOGÊNESE
    # -----------------------------------------------------

    angiogenesis()

    # -----------------------------------------------------
    # TRATAMENTOS
    # -----------------------------------------------------

    if frame > chemotherapy_start:

        apply_chemotherapy()

    if frame > radiotherapy_start:

        apply_radiotherapy()

    # -----------------------------------------------------
    # NOVA MATRIZ
    # -----------------------------------------------------

    new_grid = grid.copy()

    tumor_cells = np.argwhere(

        (
            (grid == TUMOR)
            |
            (grid == AGRESSIVO)
            |
            (grid == QUIESCENTE)
        )
    )

    # -----------------------------------------------------
    # PROCESSAMENTO
    # -----------------------------------------------------

    for x, y in tumor_cells:

        local_oxygen = oxygen[x, y]

        # NECROSE

        if local_oxygen < necrosis_threshold:

            new_grid[x, y] = NECROSE

            continue

        # QUIESCÊNCIA

        if (
            local_oxygen < quiescent_threshold
            and
            grid[x, y] != AGRESSIVO
        ):

            new_grid[x, y] = QUIESCENTE

        # RETORNO

        if (
            local_oxygen > proliferation_threshold
            and
            grid[x, y] == QUIESCENTE
        ):

            new_grid[x, y] = TUMOR

        # VIZINHOS

        neighbors = [

            (x + dx, y + dy)

            for dx in [-1, 0, 1]
            for dy in [-1, 0, 1]

            if (
                (dx != 0 or dy != 0)
                and
                (0 <= x + dx < grid_size)
                and
                (0 <= y + dy < grid_size)
            )
        ]

        empty_neighbors = [

            (nx, ny)

            for nx, ny in neighbors

            if grid[nx, ny] == VAZIO
        ]

        # MUTAÇÃO

        if grid[x, y] == TUMOR:

            if np.random.random() < mutation_probability:

                new_grid[x, y] = AGRESSIVO

        # MIGRAÇÃO

        if len(empty_neighbors) > 0:

            if np.random.random() < migration_probability:

                nx, ny = empty_neighbors[
                    np.random.randint(
                        len(empty_neighbors)
                    )
                ]

                new_grid[nx, ny] = grid[x, y]

        # PROLIFERAÇÃO

        if local_oxygen > proliferation_threshold:

            if len(empty_neighbors) > 0:

                if grid[x, y] == AGRESSIVO:

                    growth = aggressive_growth

                elif grid[x, y] == QUIESCENTE:

                    growth = 0.01

                else:

                    growth = growth_probability

                if np.random.random() < growth:

                    nx, ny = empty_neighbors[
                        np.random.randint(
                            len(empty_neighbors)
                        )
                    ]

                    new_grid[nx, ny] = grid[x, y]

    grid = new_grid

    # =====================================================
    # ESTATÍSTICAS
    # =====================================================

    tumor_count = np.sum(grid == TUMOR)

    aggressive_count = np.sum(grid == AGRESSIVO)

    necrosis_count = np.sum(grid == NECROSE)

    mean_oxygen = np.mean(oxygen)

    tumor_history.append(tumor_count)

    aggressive_history.append(aggressive_count)

    necrosis_history.append(necrosis_count)

    oxygen_history.append(mean_oxygen)

    time_history.append(frame)

    # =====================================================
    # IA
    # =====================================================

    model = train_ai()

    prediction_text = ""

    if model is not None:

        prediction = int(
            model.predict(
                np.array([[frame + 30]])
            )[0]
        )

        prediction_text = (
            f"IA prevê: {prediction}"
        )

    # =====================================================
    # LIMPAR EIXOS
    # =====================================================

    ax1.clear()
    ax2.clear()
    ax3.clear()
    ax4.clear()

    # =====================================================
    # MAPA TUMORAL
    # =====================================================

    ax1.imshow(
        grid,
        cmap=cmap,
        interpolation='nearest'
    )

    ax1.set_title(
        f"Crescimento Tumoral\nFrame: {frame}"
    )

    ax1.axis('off')

    # =====================================================
    # EVOLUÇÃO
    # =====================================================

    ax2.plot(
        time_history,
        tumor_history,
        label='Tumor'
    )

    ax2.plot(
        time_history,
        aggressive_history,
        label='Agressivo'
    )

    ax2.plot(
        time_history,
        necrosis_history,
        label='Necrose'
    )

    ax2.set_title(
        f"Evolução Tumoral\n{prediction_text}"
    )

    ax2.legend()

    # =====================================================
    # HISTOGRAMA
    # =====================================================

    labels = [
        'Tumor',
        'Agressivo',
        'Necrose',
        'Vasos',
        'Quiescente'
    ]

    values = [

        np.sum(grid == TUMOR),

        np.sum(grid == AGRESSIVO),

        np.sum(grid == NECROSE),

        np.sum(grid == VASO),

        np.sum(grid == QUIESCENTE)
    ]

    ax3.bar(labels, values)

    ax3.set_title(
        "Distribuição Celular"
    )

    # =====================================================
    # OXIGÊNIO
    # =====================================================

    ax4.imshow(
        oxygen,
        cmap='viridis'
    )

    ax4.set_title(
        "Mapa de Oxigênio (PDE)"
    )

    ax4.axis('off')


# =========================================================
# ANIMAÇÃO
# =========================================================

anim = FuncAnimation(

    fig,

    update,

    frames=180,

    interval=120,

    repeat=False
)


# =========================================================
# SALVAR GIF
# =========================================================

print("\nSalvando GIF...")

writer = PillowWriter(fps=10)

anim.save(
    "tumor_pde_simulation.gif",
    writer=writer
)

print("\nGIF salvo com sucesso!")

print("\nArquivo:")
print("tumor_pde_simulation.gif")


# =========================================================
# MOSTRAR ÚLTIMO FRAME
# =========================================================

plt.tight_layout()

plt.show()


# =========================================================
# INTERPRETAÇÃO
# =========================================================

"""
NOVO MODELO PDE:

dO/dt = D∇²O - kC

Agora o oxigênio:
- difunde realisticamente
- forma gradientes
- cria hipóxia realista
- produz necrose central

O modelo aproxima-se de:
- Mathematical Oncology
- Hybrid PDE-CA Models
- Computational Tumor Modeling
"""
