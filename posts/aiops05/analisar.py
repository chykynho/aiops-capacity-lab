"""AIOps 05 — data drift e estabilidade do detector, sem dados privados.
Uso: python posts/aiops05/analisar.py (a partir da raiz do repositorio)
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp, spearmanr
from sklearn.preprocessing import RobustScaler
from sklearn.ensemble import IsolationForest
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RECURSOS={"cpu":"hist_cpu.csv","memoria":"hist_mem.csv","disco":"hist_disk.csv"}
SEED=42

def psi_quantile(a,b,bins=6):
    """PSI com intervalos baseados na referência e suavização para evitar log(0)."""
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
    edges=np.unique(np.quantile(a,np.linspace(0,1,bins+1)))
    if len(edges)<3:return float('nan')
    edges[0]=-np.inf; edges[-1]=np.inf
    ac=np.histogram(a,bins=edges)[0];bc=np.histogram(b,bins=edges)[0]
    pa=(ac+0.5)/(len(a)+0.5*len(ac)); pb=(bc+0.5)/(len(b)+0.5*len(bc))
    return float(np.sum((pb-pa)*np.log(pb/pa)))

def analisar(raiz=Path('.'),salvar=True):
    raiz=Path(raiz).resolve();pasta=raiz/'data'/'public_demo'
    inv=pd.read_csv(pasta/'vms_inventario.csv')
    assert len(inv)==253 and inv.vm.nunique()==253, 'Inventário público deve conter 253 VMs únicas'
    periodos=[];dados={};tabelas=[]
    for nome,arq in RECURSOS.items():
        df=pd.read_csv(pasta/arq)
        df['timestamp']=pd.to_datetime(df['timestamp'],errors='raise')
        assert not df.duplicated(['vm','timestamp']).any(),f'Duplicação em {nome}'
        assert df['used_pct'].between(0,100).all(),f'Percentuais inválidos em {nome}'
        dados[nome]=df
        periodos.append(set(df.timestamp.unique()))
    dias=sorted(set.intersection(*periodos))
    assert len(dias)>=14, 'Dados insuficientes para separar duas janelas'
    corte=len(dias)//2;janela1=set(dias[:corte]);janela2=set(dias[corte:])
    min_obs=5
    por_vm={}
    resumo=[]
    for recurso,df in dados.items():
        x=df[df.timestamp.isin(janela1)];y=df[df.timestamp.isin(janela2)]
        cx=x.groupby('vm').used_pct.agg(['median','count']);cy=y.groupby('vm').used_pct.agg(['median','count'])
        merged=cx[['median','count']].join(cy[['median','count']],lsuffix='_t1',rsuffix='_t2',how='inner')
        merged=merged[(merged.count_t1>=min_obs)&(merged.count_t2>=min_obs)]
        por_vm[recurso]=merged[['median_t1','median_t2']].rename(columns={'median_t1':f'{recurso}_t1','median_t2':f'{recurso}_t2'})
        # As janelas usam todos os registros das VMs elegiveis deste recurso.
        elig=set(merged.index)
        a=x[x.vm.isin(elig)].used_pct.to_numpy();b=y[y.vm.isin(elig)].used_pct.to_numpy()
        ks=ks_2samp(a,b)
        resumo.append({'recurso':recurso,'vm_elegiveis':len(elig),'n_t1':len(a),'n_t2':len(b),
                       'mediana_t1':float(np.median(a)),'mediana_t2':float(np.median(b)),
                       'psi':psi_quantile(a,b),'ks_stat':float(ks.statistic),'ks_p':float(ks.pvalue)})
    matriz=inv[['vm','cluster','host']].set_index('vm')
    for r,t in por_vm.items():matriz=matriz.join(t,how='left')
    colunas=[f'{r}_{t}' for r in RECURSOS for t in ['t1','t2']]
    elig=matriz[colunas].notna().all(axis=1)
    validas=matriz.loc[elig].copy()
    assert len(validas)==221, f'Esperadas 221 VMs completas na base pública; foram {len(validas)}'
    for r in RECURSOS:
        validas[f'delta_{r}_pp']=validas[f'{r}_t2']-validas[f'{r}_t1']
    validas['mudanca_8pp']=(validas[[f'delta_{r}_pp' for r in RECURSOS]].abs()>=8).any(axis=1)
    # Ajusta apenas na janela T1 e aplica o detector congelado em T2.
    c1=[f'{r}_t1' for r in RECURSOS];c2=[f'{r}_t2' for r in RECURSOS]
    scaler=RobustScaler().fit(validas[c1].to_numpy());X1=scaler.transform(validas[c1].to_numpy());X2=scaler.transform(validas[c2].to_numpy())
    model=IsolationForest(n_estimators=200,contamination=0.05,random_state=SEED).fit(X1)
    validas['score_t1']=model.decision_function(X1)
    validas['score_t2']=model.decision_function(X2)
    validas['anomalia_t1']=model.predict(X1)==-1
    validas['anomalia_t2']=model.predict(X2)==-1
    antes=set(validas.index[validas.anomalia_t1]);depois=set(validas.index[validas.anomalia_t2]);inter=antes&depois
    corr=spearmanr(validas.score_t1,validas.score_t2).statistic
    resumo_df=pd.DataFrame(resumo)
    indicadores={
        'tipo':'DEMONSTRAÇÃO 100% SINTÉTICA','vms_inventario':len(inv),'vms_elegiveis':len(validas),
        'datas_t1':[str(pd.Timestamp(dias[0]).date()),str(pd.Timestamp(dias[corte-1]).date())],
        'datas_t2':[str(pd.Timestamp(dias[corte]).date()),str(pd.Timestamp(dias[-1]).date())],
        'janelas_dias':[len(janela1),len(janela2)],
        'vms_mudanca_mediana_8pp':int(validas.mudanca_8pp.sum()),
        'anomalias_t1':len(antes),'anomalias_t2':len(depois),'anomalias_em_ambas':len(inter),
        'jaccard_alertas':float(len(inter)/len(antes|depois)) if antes|depois else 1.0,
        'correlacao_spearman_scores':float(corr),
        'observacao':'PSI/KS indicam mudança na distribuição; sem rótulos de incidentes, não medimos qualidade preditiva nem concept drift.'
    }
    if salvar:
        out=raiz/'posts'/'aiops05'/'resultados';out.mkdir(parents=True,exist_ok=True)
        resumo_df.round(6).to_csv(out/'resumo_distribuicao.csv',index=False)
        validas.reset_index()[['vm','mudanca_8pp','score_t1','score_t2','anomalia_t1','anomalia_t2']+[f'delta_{r}_pp' for r in RECURSOS]].round(5).to_csv(out/'triagem_sintetica.csv',index=False)
        (out/'indicadores.json').write_text(json.dumps(indicadores,indent=2,ensure_ascii=False),encoding='utf-8')
        # Gráficos em alta resolução com margens amplas e escalas adequadas.
        # O PSI desta base é muito pequeno: jamais somar deslocamentos
        # fixos (como +0.005) à posição dos rótulos sem ajustar os limites.
        nomes={'cpu':'CPU','memoria':'Memória','disco':'Disco'}
        cores={'cpu':'#19A9D2','memoria':'#24A37D','disco':'#E3AF30'}
        labels=[nomes.get(str(r),str(r)) for r in resumo_df.recurso]
        valores=resumo_df.psi.to_numpy(dtype=float)
        limite=max(float(np.nanmax(valores))*1.30,0.001)
        fig,ax=plt.subplots(figsize=(11,5.8),facecolor='white')
        fig.subplots_adjust(left=.20,right=.90,top=.79,bottom=.19)
        ys=np.arange(len(labels))
        barras=ax.barh(ys,valores,height=.51,color=[cores.get(r,'#168BC0') for r in resumo_df.recurso])
        ax.invert_yaxis()
        ax.set_yticks(ys,labels,fontsize=16,fontweight='bold')
        ax.set_xlim(0,limite)
        ax.set_xlabel('PSI (Population Stability Index)',fontsize=13,labelpad=12)
        ax.set_title('Mudança na distribuição por recurso',loc='left',fontsize=19,fontweight='bold',pad=22)
        fig.text(.20,.89,'Duas janelas de 14 dias · 221 VMs elegíveis · base 100% sintética',fontsize=11,color='#566579')
        for barra,v in zip(barras,valores):
            ax.text(v+limite*.018,barra.get_y()+barra.get_height()/2,
                    f'{v:.4f}'.replace('.',','),va='center',fontsize=15,fontweight='bold',color='#182638')
        ax.grid(axis='x',alpha=.16)
        ax.set_axisbelow(True)
        ax.spines[['top','right','left']].set_visible(False)
        ax.tick_params(axis='y',length=0)
        fig.text(.20,.07,'PSI baixo nas três métricas; isso não comprova qualidade preditiva.',fontsize=10,color='#566579')
        fig.savefig(out/'psi_recursos.png',dpi=180,facecolor='white')
        plt.close(fig)

        fig,ax=plt.subplots(figsize=(9.5,6.7),facecolor='white')
        fig.subplots_adjust(left=.15,right=.94,top=.83,bottom=.16)
        x=validas.score_t1.to_numpy();y=validas.score_t2.to_numpy()
        mascara=validas.anomalia_t2.to_numpy(dtype=bool)
        ax.scatter(x[~mascara],y[~mascara],s=37,alpha=.60,label='Não sinalizada em T2',color='#1689d3')
        ax.scatter(x[mascara],y[mascara],s=65,alpha=.93,label='Sinalizada em T2',color='#ef654e',edgecolor='white',linewidth=.5)
        ax.axhline(0,ls='--',color='#dd5943',lw=1.5,alpha=.75)
        ax.axvline(0,ls='--',color='#dd5943',lw=1.5,alpha=.75)
        ax.set_xlabel('Score Isolation Forest · T1',fontsize=12,labelpad=10)
        ax.set_ylabel('Score Isolation Forest · T2',fontsize=12,labelpad=10)
        ax.set_title('Estabilidade das pontuações de anomalia',loc='left',fontsize=18,fontweight='bold',pad=22)
        fig.text(.15,.90,'Mesmo modelo treinado em T1 e aplicado em T2 · 221 VMs sintéticas',fontsize=11,color='#566579')
        ax.grid(alpha=.14)
        ax.legend(loc='lower right',fontsize=10,frameon=True)
        fig.savefig(out/'scores_isolation_forest.png',dpi=180,facecolor='white')
        plt.close(fig)
    return indicadores,resumo_df,validas

if __name__=='__main__':
    i,r,v=analisar(Path(__file__).resolve().parents[2]);print(json.dumps(i,ensure_ascii=False,indent=2));print(r.round(4).to_string(index=False))
