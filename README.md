1. Propósito General

El sistema funciona como una plataforma de gestión de datos que transforma archivos de Excel (generalmente desorganizados o con celdas combinadas) en bases de datos limpias (formato CSV) para generar indicadores clave de desempeño (KPIs).
2. Estructura de Datos (Directorios)

La aplicación organiza la información en cuatro categorías principales almacenadas en la carpeta data/:

    Grupo Entrega Real: Seguimiento de pedidos y entregas.

    Referencias Pendientes: Listado de productos por completar.

    Unidades cortadas: Registro de la producción inicial.

    WIP (Work In Progress): Trabajo en proceso.

3. Lógica de Procesamiento (ETL y Processor)

Esta es la inteligencia del proyecto. Se encarga de la limpieza de datos a través de los archivos core/etl.py y core/processor.py:

    Normalización de Columnas: Convierte todos los encabezados a mayúsculas, elimina espacios extra, quita tildes y elimina columnas duplicadas o vacías.

    Identificación Automática: Determina si la información pertenece a la marca STOP o YOYO analizando el nombre del archivo subido.

    Limpieza de Texto: Elimina prefijos numéricos comunes en sistemas contables (por ejemplo, transforma "001 - JULIO" en "JULIO").

    Conversión de Tipos: Asegura que las fechas sean objetos de tiempo y que las cantidades sean números enteros para evitar errores en los cálculos.

    Manejo de Excel (Forward Fill): Resuelve el problema de las celdas combinadas en Excel rellenando los valores hacia abajo para que cada fila tenga la información completa de su categoría.

4. Interfaz de Usuario (App Principal)

El archivo app.py gestiona la visualización y la interacción:

    Menú de Navegación: Utiliza una barra lateral para moverse entre el Dashboard general y las vistas detalladas de cada sección.

    Carga de Archivos: Permite subir múltiples archivos Excel simultáneamente. Al procesarlos, los convierte internamente a CSV para optimizar la lectura futura.

    Dashboard Interactivo:

        Indicador de Cumplimiento: Un gráfico de tipo "Gauge" que muestra el porcentaje total de cumplimiento (Unidades Completas vs. Unidades Ordenadas).

        Análisis por Colección: Gráficos de barras que comparan lo ordenado contra lo completado por cada colección.

        Filtros Dinámicos: Permite segmentar la información por Marca, Mes, Colección o Grupo de Entrega.

    Gestión de Críticos: Una tabla automática que detecta las Órdenes de Producción (O.P.) que ya vencieron (según la fecha de terminación) y que aún tienen unidades pendientes.

5. Flujo de Trabajo Típico

    El usuario selecciona una sección (ej. "Unidades cortadas").

    Sube uno o varios archivos Excel extraídos de su sistema de gestión.

    Presiona "Procesar y Guardar", lo cual activa la limpieza y guarda los datos en el servidor local.

    La aplicación actualiza el Dashboard, permitiendo al usuario ver el estado real de la operación y tomar decisiones sobre los pedidos retrasados.

Resumen Técnico

    Backend: Python con Pandas para manipulación de datos y Regex para limpieza de texto.

    Frontend: Streamlit para la interfaz web.

    Visualización: Plotly para gráficos dinámicos y profesionales.

    Almacenamiento: Sistema de archivos local basado en CSV.
