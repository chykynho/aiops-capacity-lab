# AIOps: primeiro laboratório Wine

Experimento extraído das sete primeiras células do notebook original (introdução, importações, PCA + K-Means e t-SNE). **Não contém o experimento VMware**.

## Executar no WSL / VS Code

1. Ative `conda activate aiops`.
2. Na pasta deste material, execute `python -m pip install -e .`.
3. Abra `notebooks/Laboratorio_Wine_PCA_KMeans_tSNE.ipynb` no VS Code e selecione o kernel Python (AIOps).
4. Execute as células em ordem.

## Resultados registrados na execução de 02/10/2026

- PCA com dois componentes: variância explicada 0,5496.
- Silhouette treino: 0,5779.
- Silhouette teste: 0,5252.
- ARI teste, usando rótulos apenas como referência externa: 0,8575.

Os resultados são específicos ao dataset Wine, não a métricas VMware. No gráfico t-SNE, as cores representam as classes conhecidas, e não clusters previstos.
