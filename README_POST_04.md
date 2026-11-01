# 📊 AIOps #04 — Mudanças de comportamento em VMs

![AIOps](https://img.shields.io/badge/AIOps-Lab_04-14b8a6) ![Dataset](https://img.shields.io/badge/dados-253_VMs_sintéticas-blue) ![Status](https://img.shields.io/badge/status-demonstração-green)

> Continuação de **#01 perfis → #02 anomalias → #03 priorização → #04 análise temporal**.

## 🧭 Objetivo

Comparar a mediana da utilização de CPU, memória e disco nas duas metades cronológicas do histórico de cada VM, para levantar hipóteses de mudança operacional. Esta é uma **triagem didática**, não um detector validado de data drift nem de incidentes.

## 📁 Conteúdo

| Item | Conteúdo |
|---|---|
| `notebooks/Laboratorio_AIOps_04_Mudanca_Comportamento.ipynb` | Notebook reproduzível |
| `graficos/` | Gráficos calculados e resumo CSV |
| `data/public_demo/` | 7 CSVs públicos sintéticos (já disponíveis no repositório) |

## ▶️ Executar no laboratório existente

```bash
cd ~/PythonProjects/aiops_capacity_lab
conda activate aiops
python -m pip install .
```

Abra o notebook no VS Code e execute as células. Os resultados dependem da versão dos CSVs. **Não publicar dados de `data/pseudonimizados/`.**

## 🔍 Como interpretar

Uma diferença de mediana acima de 8 pontos percentuais é uma hipótese de mudança, não prova de falha. Verifique coleta, duração da janela, sazonalidade, intervenções recentes e impacto sobre a aplicação.

## 📚 Referências

- [Documentação pandas — GroupBy](https://pandas.pydata.org/docs/reference/groupby.html)
- [scikit-learn — detecção de outliers](https://scikit-learn.org/stable/modules/outlier_detection.html)
