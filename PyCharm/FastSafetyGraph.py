# Importar las librerias necesarias
import pickle
import osmnx as ox
#from geopy.geocoders import Nominatim
#from geopy.exc import GeocoderTimedOut
from geopy.geocoders import GeoNames
geolocator = GeoNames(username='andrecnf')  # Register at Geonames
import pandas as pd
import sys
import os
import numpy as np
import time
import difflib
from unidecode import unidecode
import math
import networkx as nx
import matplotlib.cm as cm
from difflib import SequenceMatcher


def read_graph_data():
    G_in = open(
        '/Users/AndreCNF/OneDrive/UNAL/Optimización y Control en Sistemas Distribuidos en Red/Proyecto/PyCharm/G_DirecSegrTrafPolicia.pickle',
        'rb')
    
    G_guardado = pickle.load(G_in)

    CentroBarrioEstrs_in = open(
        '/Users/AndreCNF/OneDrive/UNAL/Optimización y Control en Sistemas Distribuidos en Red/Proyecto/PyCharm/CentroBarrioEstrs.pickle',
        'rb')

    CentroBarrioEstrs = pickle.load(CentroBarrioEstrs_in)

    return G_guardado, CentroBarrioEstrs


def read_data_excels():
    #############################################################################################
    # Leer archivo de Excel con los nombres de las localidades de Bogotá
    #############################################################################################
    script_dir = sys.path[0]
    xlsx_path = os.path.join(script_dir, '/Users/AndreCNF/OneDrive/UNAL/Optimización y Control en Sistemas Distribuidos en Red/Proyecto/data/DICE015A-ProyeccionesLocalidades-2016.xls.xlsx')
    df_Localidades = pd.read_excel(xlsx_path, header=4)
    # print(df_Localidades.head())

    #############################################################################################
    # Leer archivo de Excel con los datos de crimenes en las localidades de Bogotá
    #############################################################################################
    script_dir = sys.path[0]
    xlsx_path = os.path.join(script_dir, '/Users/AndreCNF/OneDrive/UNAL/Optimización y Control en Sistemas Distribuidos en Red/Proyecto/data/Seguridad_Bogota.xlsx')
    df_SeguridadLocal = pd.read_excel(xlsx_path, sheetname='Seguridad (sin accidentes)')
    # print(df_SeguridadLocal.head())

    #############################################################################################
    # Leer archivo de Excel con los nombres de las localidades y barrios de Bogotá
    #############################################################################################
    script_dir = sys.path[0]
    xlsx_path = os.path.join(script_dir, '/Users/AndreCNF/OneDrive/UNAL/Optimización y Control en Sistemas Distribuidos en Red/Proyecto/data/Barrios y localidades Bogotá.xlsx')
    df_LocalBarrios = pd.read_excel(xlsx_path, header=0)
    # df_LocalBarrios.head()

    #############################################################################################
    # Leer archivo de Excel con la repartición de la población por estratos, en cada localidad
    #############################################################################################
    script_dir = sys.path[0]
    xlsx_path = os.path.join(script_dir, '/Users/AndreCNF/OneDrive/UNAL/Optimización y Control en Sistemas Distribuidos en Red/Proyecto/data/DICE014-Estratos.xlsx')
    df_Estratos = pd.read_excel(xlsx_path, sheetname='11Corregido', header=0)
    # print(df_Estratos.head())

    #############################################################################################
    # Leer archivo de Excel sobre la densidad poblacional, que permite inferir el tráfico
    #############################################################################################
    script_dir = sys.path[0]
    xlsx_path = os.path.join(script_dir, '/Users/AndreCNF/OneDrive/UNAL/Optimización y Control en Sistemas Distribuidos en Red/Proyecto/data/Información trafico_relevante.xlsx')
    df_DensTrafico = pd.read_excel(xlsx_path, header=0)
    # print(df_DensTrafico.head())

    # Guardar nombres de las localidades de Bogota
    Localidad = df_Localidades['Nombres correctos'][1:21]
    
    # Guardar población estimada de cada localidad
    Poblacion = df_Localidades[2017][1:21]

    #############################################################################################
    # Atribucion de números de crimenes y densidad criminal a cada barrio
    #############################################################################################
    
    # Número total de crimenes
    CrimesLocalidad = np.zeros((len(Localidad)+1))
    
    # Número de crimenes por la cantidad de habitantes/población
    DensidadCriminal = np.zeros((len(Localidad)+1))
    
    for i in range(1, (len(Localidad)+1)):
        CrimesLocalidad[i] = df_SeguridadLocal[(df_SeguridadLocal['geo_padre_nombre']=='BOGOTÁ, D.C.') & (df_SeguridadLocal['geografia_nombre']==('LOCALIDAD ' + unidecode(Localidad[i]).upper()))]['Valor'].sum()
        
        # Dividir por el total de población de la localidad
        DensidadCriminal[i] = CrimesLocalidad[i] / Poblacion[i]
        # print('Crimenes en', Localidad[i], ': ', CrimesLocalidad[i], ';  Densidad criminal: ', DensidadCriminal[i])
        # print(Localidad[i], \|  \, \Densidad criminal: \, DensidadCriminal[i], \;  Porcentaje Estrato Bajo: \, LocPorcEstratoBajo[i])
        i += 1

    #############################################################################################
    # Guardar lista de direcciones posibles de Bogotá, para después añadir al grafo
    #############################################################################################
    
    Direccion = [None for i in range(831)]
    
    for i in range(831):
        if df_LocalBarrios['Localidad'][i] == 'Rafael Uribe':
            Direccion[i] = df_LocalBarrios['Barrio'][i] + ', Rafael Uribe Uribe, Bogotá, Bogotá DC, Colombia'
        elif df_LocalBarrios['Localidad'][i] == 'Candelaria':
            Direccion[i] = df_LocalBarrios['Barrio'][i] + ', La Candelaria, Bogotá, Bogotá DC, Colombia'
        else:
            Direccion[i] = df_LocalBarrios['Barrio'][i] + ', ' + df_LocalBarrios['Localidad'][i] + ', Bogotá, Bogotá DC, Colombia'
            
        # if i < 20:
        #     print(Direccion[i])

    return df_Localidades, df_SeguridadLocal, df_LocalBarrios, df_Estratos, df_DensTrafico, Localidad, Poblacion, \
           CrimesLocalidad, DensidadCriminal, Direccion


# get a color for each node
def get_color_list(n, color_map='nipy_spectral', start=0, end=1):
    return [cm.get_cmap(color_map)(x) for x in np.linspace(start, end, n)]


# Calcular porcentaje de similitud entre dos frases
def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


# Cálculo de la distancia euclidea entre los puntos 'x' y 'y'
def DistEucl(x, y):
    distance = math.sqrt((x[0] - y[0]) ** 2 + (x[1] - y[1]) ** 2)
    return distance


#############################################################################################
# Función que imprime el progreso, en percentaje, del loop
#############################################################################################
def PrintProgress(i, max_i):
    sys.stdout.write('\\r' + str( (i / max_i ) * 100 ) + '%' + ' ' * 20)
    sys.stdout.flush() # important


#############################################################################################
# Loop para poner todos los datos de crimenes de las localidades en cada nodo correspondiente
#############################################################################################
def apply_crime_logs(G_guardado, DensidadCriminal, Localidad, crime_weight=100):
    # Variable que indica el número del nodo del grafo en que se va
    contaje = 0

    for i in G_guardado.nodes():
        # Saltar iteración si el nodo actual ya tuviere un valor de inseguridad (para continuar con proceso del día anterior)
        # if 'inseguridad' in G_guardado.node[i]:
        #     continue

        if 'inseguridad' not in G_guardado.node[i] and ('type' not in G_guardado.node[i] or
                                                       ('type' in G_guardado.node[i] and 'policia' not in G_guardado.node[i]['type'])):
            G_guardado.node[i]['inseguridad'] = 0

        for j in range(1, (len(Localidad)+1)):
            if 'direccion' in G_guardado.node[i]:
                if unidecode(Localidad[j]) in G_guardado.node[i]['direccion'] or Localidad[j] in G_guardado.node[i]['direccion']:
                    G_guardado.node[i]['inseguridad'] = crime_weight * DensidadCriminal[j]
                    break

        contaje += 1
        PrintProgress(contaje, len(G_guardado.nodes()))

    return G_guardado
        
        
def get_low_strata_data(df_LocalBarrios, df_Estratos, Direccion, Localidad):
    #############################################################################################
    # Guardar en variables los porcentajes de personas de estratos bajos por barrio
    #############################################################################################
    
    closest = None
    PorcEstratoBajo = [0 for i in range(len(df_LocalBarrios['Barrio']))]
    LocPorcEstratoBajo = [0 for i in range(len(Localidad)+1)]
    EstrBarPorcEstratoBajo = [0 for i in range(len(df_Estratos['NOM_UPZ'])-2)]
    
    for i in range(len(df_Estratos['NOM_UPZ'])-2):
        flag_match = 0
    
        for j in range(len(df_LocalBarrios['Barrio'])):
            if similar(Direccion[j].split(',')[0], df_Estratos['NOM_UPZ'][i]) > 0.8 and similar(Direccion[j].split(',')[1], df_Estratos['NOM_LOC'][i]) > 0.8:            
                flag_match = 1
                PorcEstratoBajo[j] = (df_Estratos['Personas Sin estrato'][i] + df_Estratos['Personas 1. Bajo - bajo'][i] +
                                      0.5 * df_Estratos['Personas 2. Bajo'][i]) / df_Estratos['Total Personas'][i]
                break
    
    for k in range(1, len(Localidad)+1):
        LocPorcEstratoBajo[k] = (df_Estratos[df_Estratos['NOM_LOC']==Localidad[k]]['Personas Sin estrato'].sum() +
                                df_Estratos[df_Estratos['NOM_LOC']==Localidad[k]]['Personas 1. Bajo - bajo'].sum() +
                                0.5 * df_Estratos[df_Estratos['NOM_LOC']==Localidad[k]]['Personas 2. Bajo'].sum()) / \
                                df_Estratos[df_Estratos['NOM_LOC']==Localidad[k]]['Total Personas'].sum()
        
    for i in range(len(df_Estratos['NOM_UPZ'])-2):
        EstrBarPorcEstratoBajo[i] = (df_Estratos['Personas Sin estrato'][i] + df_Estratos['Personas 1. Bajo - bajo'][i] +
                                      0.5 * df_Estratos['Personas 2. Bajo'][i]) / df_Estratos['Total Personas'][i]

    return PorcEstratoBajo, LocPorcEstratoBajo, EstrBarPorcEstratoBajo


###################################################################################################
# Añadir información de los porcentajes de personas de estratos bajos a la inseguridad de los nodos
###################################################################################################
def apply_low_strata_data(G_guardado, PorcEstratoBajo, LocPorcEstratoBajo, EstrBarPorcEstratoBajo, Localidad,
                          CentroBarrioEstrs, Direccion, df_Estratos, estr_peso=60):
    # ~ Distancia maxima entre dos barrios
    dist_max = DistEucl((4.681544, -74.050801), (4.672643, -74.052690))

    # Peso de la importancia del porcentaje de estrato social bajo
    # estr_peso = 30
    # estr_peso = 50

    k_min = -1

    for i in G_guardado.nodes():
        if 'type' in G_guardado.node[i]:
            if 'policia' in G_guardado.node[i]['type']:
                continue

        for j in range(len(Direccion)):
            if G_guardado.node[i]['direccion'] == Direccion[j]:
                if PorcEstratoBajo[j] is not 0:
                    G_guardado.node[i]['inseguridad'] += estr_peso * PorcEstratoBajo[j]
                else:
                    min = float('inf')

                    # Añadir información de estratos del barrio más cercano mencionado en df_Estratos
                    for k in range(len(df_Estratos['NOM_UPZ'])-2):
                        if DistEucl((G_guardado.node[i]['y'], G_guardado.node[i]['x']), CentroBarrioEstrs[k]) < min:
                            min = DistEucl((G_guardado.node[i]['y'], G_guardado.node[i]['x']), CentroBarrioEstrs[k])
                            Direccion_Cercana = df_Estratos['NOM_UPZ'][k] + ', ' + df_Estratos['NOM_LOC'][k] + ', ' + 'Bogotá, Bogotá DC, Colombia'
                            k_min = k

                    if min < dist_max:
                        G_guardado.node[i]['inseguridad'] += estr_peso * EstrBarPorcEstratoBajo[k_min]
                    else:
                        # Añadir información de estratos de la localidad entera
                        for k in range(1, len(Localidad)+1):
                            if unidecode(Localidad[k]) in G_guardado.node[i]['direccion'] or Localidad[k] in G_guardado.node[i]['direccion']:
                                G_guardado.node[i]['inseguridad'] += estr_peso * LocPorcEstratoBajo[k]
    
    return G_guardado


###################################################################################################
# Calcular máximo y promédio de la inseguridad
###################################################################################################
def calc_safety_max_avg(G_guardado):

    promedio_insg = 0
    max_insg = 0

    # Contar numero de nodos que no son estaciones de policia
    count = 0

    for i in G_guardado.nodes():
        if 'inseguridad' in G_guardado.node[i]:
            promedio_insg += G_guardado.node[i]['inseguridad']

            if G_guardado.node[i]['inseguridad'] > max_insg:
                max_insg = G_guardado.node[i]['inseguridad']

            count = count + 1

    promedio_insg = promedio_insg / count
    print('Max = ', max_insg, '; Promedio: ', promedio_insg)

    return max_insg, promedio_insg


def safety_graph_plot(G_guardado, promedio_insg):
    nc = []
    n_ec = []
    ns = []

    # Recta occidente
    def yo(x):
        return 0.659013 * x + (-77.2722)

    # Recta norte
    def yn(x):
        return -5.87413 * x + (-45.6912)

    # Recta norte
    def yor(x):
        return 0.200466 * x + (-74.926)

    # Recta sur
    def ys(x):
        return -22.0299 * x + (24.2968)

    for i in G_guardado.nodes():
        if G_guardado.node[i]['x'] < yor(G_guardado.node[i]['y']) and G_guardado.node[i]['x'] < yn(G_guardado.node[i]['y']) and G_guardado.node[i]['x'] > yo(G_guardado.node[i]['y']) and G_guardado.node[i]['x'] > ys(G_guardado.node[i]['y']):
            if 'type' in G_guardado.node[i]:
                if G_guardado.node[i]['type'] == 'policia':
                    nc.append('#FFFF00')
                    n_ec.append('#363600')
                    ns.append(5)
            elif G_guardado.node[i]['inseguridad'] > 2 * promedio_insg:
                nc.append('#AF0000')
                ns.append(0.5)
            elif G_guardado.node[i]['inseguridad'] > promedio_insg:
                nc.append('#FF5A5A')
                ns.append(0.5)
            elif G_guardado.node[i]['inseguridad'] < promedio_insg / 4.5:
                nc.append('#7CFC00')
                ns.append(0.5)
            else:
                nc.append('#336699')
                ns.append(0.5)
        else:
            nc.append('#336699')
            ns.append(0.5)

    fig, ax = ox.plot_graph(G_guardado, node_size=ns, node_color=nc, node_zorder=2)
    fig.savefig('GrafoBogotaSeguridad_15JulyV3.png', format='png', dpi=500)
    

###################################################################################################
# Dibujo de una ruta entre Virrey y Monserrate, con los pesos ya aplicados
###################################################################################################
def draw_best_path(G_guardado, orig=(4.675348, -74.058797), dest=(4.604647, -74.060380), file_name='GrafoBogotaRutaConPesos'):
    # La ruta no va directa, se va un poco por fuera para evitar la inseguridad de ciertas zonas de 
    # Chapinero (al menos es lo que parece)
    
    # punto_partida = (4.675348, -74.058797)
    # punto_llegada = (4.604647, -74.060380)
    origin_node = ox.get_nearest_node(G_guardado, orig)
    destination_node = ox.get_nearest_node(G_guardado, dest)
    
    # find the route between these nodes then plot it
    route = nx.shortest_path(G_guardado, origin_node, destination_node, weight='peso')
    fig, ax = ox.plot_graph_route(G_guardado, route)
    # fig.savefig('GrafoBogotaRutaConPesos.png', format='png', dpi=500)
    fig.savefig(file_name + '.png', format='png', dpi=500)


def apply_edge_weights(G_guardado, dist_w=1, saf_w=1, traf_w=(1 / 5000)):
    ###################################################################################################
    # Asignación de pesos a los edges/calles, con base en distancias, inseguridad y trafico
    ###################################################################################################

    for i, j in G_guardado.edges():
        G_guardado.edge[i][j][0]['peso'] = dist_w * G_guardado.edge[i][j][0]['length'] + \
                                        saf_w * ((G_guardado.node[i]['inseguridad'] + G_guardado.node[j]['inseguridad']) / 2) \
                                        + traf_w * ((G_guardado.node[i]['trafico'] + G_guardado.node[j]['trafico']) / 2)
    
    return G_guardado


G_guardado, CentroBarrioEstrs = read_graph_data()
print('Graph and CentroBarrioEstrs have been read.')
df_Localidades, df_SeguridadLocal, df_LocalBarrios, df_Estratos, df_DensTrafico, Localidad, Poblacion, \
CrimesLocalidad, DensidadCriminal, Direccion = read_data_excels()
print('Excel data files have been read.')
G_guardado = apply_crime_logs(G_guardado, DensidadCriminal, Localidad, crime_weight=100)
print('Crime logs data has been applied to the graph.')
PorcEstratoBajo, LocPorcEstratoBajo, EstrBarPorcEstratoBajo = get_low_strata_data(df_LocalBarrios, df_Estratos, Direccion, Localidad)
print('Low strata data has been fetched.')
G_guardado = apply_low_strata_data(G_guardado, PorcEstratoBajo, LocPorcEstratoBajo, EstrBarPorcEstratoBajo, Localidad,
                                   CentroBarrioEstrs, Direccion, df_Estratos, estr_peso=70)
print('Low strata data has been applied to the graph.')
max_insg, promedio_insg = calc_safety_max_avg(G_guardado)
safety_graph_plot(G_guardado, promedio_insg)
print('Graph safety plot has been saved.')

G_guardado = apply_edge_weights(G_guardado, dist_w=100, saf_w=1, traf_w=(1 / 5000))
draw_best_path(G_guardado, orig=(4.675348, -74.058797), dest=(4.604647, -74.060380), file_name='GrafoBogotaRutaConPesos_dist100')
print('Plotted best path with dist_w=100, saf_w=1, traf_w=(1 / 5000).')

G_guardado = apply_edge_weights(G_guardado, dist_w=1, saf_w=10, traf_w=(1 / 5000))
draw_best_path(G_guardado, orig=(4.675348, -74.058797), dest=(4.604647, -74.060380), file_name='GrafoBogotaRutaConPesos_saf10')
print('Plotted best path with dist_w=1, saf_w=10, traf_w=(1 / 5000).')

G_guardado = apply_edge_weights(G_guardado, dist_w=1, saf_w=100, traf_w=(1 / 5000))
draw_best_path(G_guardado, orig=(4.675348, -74.058797), dest=(4.604647, -74.060380), file_name='GrafoBogotaRutaConPesos_saf100')
print('Plotted best path with dist_w=1, saf_w=100, traf_w=(1 / 5000).')

G_guardado = apply_edge_weights(G_guardado, dist_w=1, saf_w=1000, traf_w=(1 / 5000))
draw_best_path(G_guardado, orig=(4.675348, -74.058797), dest=(4.604647, -74.060380), file_name='GrafoBogotaRutaConPesos_saf1000')
print('Plotted best path with dist_w=1, saf_w=1000, traf_w=(1 / 5000).')