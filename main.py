# ============================================================
# SIMULAÇÃO AVANÇADA DE CRESCIMENTO TUMORAL
# MODELO PDE + AUTÔMATO CELULAR
# ============================================================
# Autor: André Luiz Magalhães de Oliveira
# Formação: Físico Médico | Especialista em Data Science & Analytics
# Universidade de São Paulo
# ============================================================

import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.animation import FuncAnimation, PillowWriter
from matplotlib.colors import ListedColormap
from sklearn.linear_model import LinearRegression

# ============================================================
# CONFIGURAÇÕES
# ============================================================

mpl.rcParams['animation.embed_limit'] = 50
plt.rcParams["figure.figsize"] = (16, 10)

# Estados celulares
VAZIO, TUMOR, NECROSE, VASO, AGRESSIVO, QUIESCENTE = range(6)

# Parâmetros principais
grid_size = 120
growth_probability, aggressive_growth = 0.12, 0.25
D_oxygen, oxygen_consumption, dt = 0.15, 0.02, 0.1
necrosis_threshold, quiescent_threshold, proliferation_threshold = 0.10, 0.25, 0.45
mutation_probability, migration_probability = 0.001, 0.03
drug_decay, drug_kill_probability = 0.01, 0.20
radiotherapy_probability = 0.15
chemotherapy_start, radiotherapy_start = 80, 120

# Matrizes
grid = np.zeros((grid_size, grid_size))
oxygen = np.ones((grid_size, grid_size))
drug = np.zeros((grid_size, grid_size))

# Tumor inicial
grid[grid_size//2, grid_size//2] = TUMOR

# Colormap
cmap = ListedColormap(['black','red','yellow','blue','magenta','green'])

# Históricos
tumor_history, aggressive_history, necrosis_history, oxygen_history, time_history = [], [], [], [], []

# Figura
fig, (ax1, ax2, ax3, ax4) = plt.subplots(2, 2)

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def diffuse_oxygen_pde():
    global oxygen
    new_oxygen = oxygen.copy()
    for x in range(1, grid_size-1):
        for y in range(1, grid_size-1):
            laplacian = oxygen[x+1,y]+oxygen[x-1,y]+oxygen[x,y+1]+oxygen[x,y-1]-4*oxygen[x,y]
            consumption = oxygen_consumption if grid[x,y] in (TUMOR, AGRESSIVO, QUIESCENTE) else 0
            new_oxygen[x,y] = oxygen[x,y] + dt*(D_oxygen*laplacian - consumption)
    new_oxygen[[0,-1],:] = 1.0; new_oxygen[:,[0,-1]] = 1.0
    for x,y in np.argwhere(grid==VASO): new_oxygen[x,y] = 1.0
    oxygen[:] = np.clip(new_oxygen,0,1)

def diffuse_drug():
    global drug
    new_drug = drug.copy()
    for x in range(1, grid_size-1):
        for y in range(1, grid_size-1):
            laplacian = drug[x+1,y]+drug[x-1,y]+drug[x,y+1]+drug[x,y-1]-4*drug[x,y]
            new_drug[x,y] = drug[x,y] + 0.1*laplacian - drug_decay
    new_drug[[0,-1],:] = 1.0; new_drug[:,[0,-1]] = 1.0
    drug[:] = np.clip(new_drug,0,1)

def angiogenesis():
    hypoxic = np.argwhere(((grid==TUMOR)|(grid==AGRESSIVO)) & (oxygen<0.20))
    for x,y in hypoxic:
        for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx,ny = x+dx,y+dy
            if 0<=nx<grid_size and 0<=ny<grid_size and grid[nx,ny]==VAZIO and np.random.random()<0.015:
                grid[nx,ny]=VASO

def apply_chemotherapy():
    for x,y in np.argwhere((grid==TUMOR)|(grid==AGRESSIVO)|(grid==QUIESCENTE)):
        resistance = 0.6 if grid[x,y]==AGRESSIVO else 0.8 if grid[x,y]==QUIESCENTE else 0
        if np.random.random() < drug_kill_probability*drug[x,y]*(1-resistance):
            grid[x,y]=NECROSE

def apply_radiotherapy():
    for x,y in np.argwhere((grid==TUMOR)|(grid==AGRESSIVO)):
        resistance = 0.5 if grid[x,y]==AGRESSIVO else 0
        if oxygen[x,y]>0.3 and np.random.random()<radiotherapy_probability*(1-resistance):
            grid[x,y]=NECROSE

def train_ai():
    if len(tumor_history)<20: return None
    model=LinearRegression().fit(np.array(time_history).reshape(-1,1),np.array(tumor_history))
    return model

# ============================================================
# UPDATE
# ============================================================

def update(frame):
    global grid
    diffuse_oxygen_pde()
    if frame>chemotherapy_start: diffuse_drug(); apply_chemotherapy()
    if frame>radiotherapy_start: apply_radiotherapy()
    new_grid=grid.copy()
    for x,y in np.argwhere((grid==TUMOR)|(grid==AGRESSIVO)|(grid==QUIESCENTE)):
        local_oxygen=oxygen[x,y]
        if local_oxygen<necrosis_threshold: new_grid[x,y]=NECROSE; continue
        if local_oxygen<quiescent_threshold and grid[x,y]!=AGRESSIVO: new_grid[x,y]=QUIESCENTE
        if local_oxygen>proliferation_threshold and grid[x,y]==QUIESCENTE: new_grid[x,y]=TUMOR
        empty_neighbors=[(nx,ny) for dx in [-1,0,1] for dy in [-1,0,1] if (dx or dy) and 0<=x+dx<grid_size and 0<=y+dy<grid_size and grid[x+dx,y+dy]==VAZIO for nx,ny in [(x+dx,y+dy)]]
        if grid[x,y]==TUMOR and np.random.random()<mutation_probability: new_grid[x,y]=AGRESSIVO
        if empty_neighbors and np.random.random()<migration_probability: new_grid[np.random.choice(empty_neighbors)]=grid[x,y]
        if local_oxygen>proliferation_threshold and empty_neighbors:
            growth = aggressive_growth if grid[x,y]==AGRESSIVO else 0.01 if grid[x,y]==QUIESCENTE else growth_probability
            if np.random.random()<growth: new_grid[np.random.choice(empty_neighbors)]=grid[x,y]
    grid=new_grid

    # Estatísticas
    tumor_history.append(np.sum(grid==TUMOR))
    aggressive_history.append(np.sum(grid==AGRESSIVO))
    necrosis_history.append(np.sum(grid==NECROSE))
    oxygen_history.append(np.mean(oxygen))
    time_history.append(frame)

    # IA preditiva
    model=train_ai(); prediction_text=""
    if model is not None: prediction_text=f"IA prevê: {int(model.predict([[frame+30]])[0])}"

    # Plot
    ax1.clear(); ax2.clear(); ax3.clear(); ax4.clear()
    ax1.imshow(grid,cmap=cmap); ax1.set_title(f"Crescimento Tumoral\nFrame: {frame}"); ax1.axis('off')
    ax2.plot(time_history,tumor_history,label='Tumor'); ax2.plot(time_history,aggressive_history,label='Agressivo'); ax2.plot(time_history,necrosis_history,label='Necrose')
    ax2.set_title(f"Evolução Tumoral\n{prediction_text}"); ax2.legend()
    labels=['Tumor','Agressivo','Necrose','Vasos','Quiescente']
    values=[np.sum(grid==TUMOR),np.sum(grid==AGRESSIVO),np.sum(grid==NECROSE),np.sum(grid==VASO),np.sum(grid==QUIESCENTE)]
    ax3.bar(labels,values); ax3.set_title("Distribuição Celular")
    ax4.imshow(oxygen,cmap='viridis'); ax4.set_title("Mapa de Oxigênio (PDE)"); ax4.axis('off')

# ============================================================
# ANIMAÇÃO
# ============================================================

anim=FuncAnimation(fig,update,frames=180,interval=120,repeat=False)
print("\nSalvando GIF...")
anim.save("tumor_pde_simulation.gif",writer=PillowWriter(fps=10))
print("\nGIF salvo com sucesso!\nArquivo: tumor_pde_simulation.gif")
plt.tight_layout(); plt.show()
