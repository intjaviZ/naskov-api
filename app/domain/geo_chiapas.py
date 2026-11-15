"""
app/domain/geo_chiapas.py
Módulo geográfico para resolución de regiones agroclimáticas en el estado de Chiapas.
"""

def determinar_region_chiapas(lat: float, lon: float) -> str:
    """
    Determina la región agroclimática dentro del estado de Chiapas a partir de coordenadas.
    Únicamente devuelve 'Frailesca, Chiapas' si la ubicación se encuentra dentro del polígono
    geográfico de La Frailesca (Villaflores, Villa Corzo, La Concordia, El Parral, Ángel Albino Corzo).
    Para el resto del estado devuelve la región específica o 'Chiapas, México' por omisión.
    """
    # 1. La Frailesca (Villaflores, Villa Corzo, La Concordia, El Parral, Ángel Albino Corzo)
    # Rango latitudinal aprox 15.90 a 16.45, longitudinal -93.60 a -92.80
    if 15.90 <= lat <= 16.45 and -93.60 <= lon <= -92.80:
        return "Frailesca, Chiapas"

    # 2. Costa / Soconusco (Tapachula, Huixtla, Tonalá, Pijijiapan, Mapastepec, Arriaga)
    if (lat <= 15.55 and lon <= -92.05) or (lat <= 16.30 and lon <= -93.50):
        return "Costa / Soconusco, Chiapas"

    # 3. Altos de Chiapas (San Cristóbal de Las Casas, Chamula, Zinacantán, Huixtán)
    if 16.50 <= lat <= 17.15 and -92.85 <= lon <= -92.30:
        return "Altos de Chiapas"

    # 4. Centro / Metropolitana / Valles Zoque (Tuxtla Gutiérrez, Chiapa de Corzo, Ocozocoautla, Berriozábal, Cintalapa)
    if 16.45 <= lat <= 17.05 and -94.00 <= lon <= -92.90:
        return "Centro / Valles de Chiapas"

    # 5. Selva / Palenque / Maya (Palenque, Ocosingo, Salto de Agua, Chilón, Yajalón)
    if 16.40 <= lat <= 17.90 and -92.30 <= lon <= -90.40:
        return "Selva / Palenque, Chiapas"

    # 6. Norte / De Los Bosques (Pichucalco, Reforma, Juárez, Bochil, Simojovel)
    if 17.10 <= lat <= 18.00 and -93.60 <= lon <= -92.70:
        return "Norte de Chiapas"

    # 7. Sierra Mariscal (Motozintla, Siltepec, Frontera Comalapa)
    if 15.10 <= lat <= 15.80 and -92.50 <= lon <= -91.90:
        return "Sierra de Chiapas"

    # 8. Meseta Comiteca / Llanos (Comitán, Las Margaritas, La Trinitaria)
    if 15.80 <= lat <= 16.50 and -92.40 <= lon <= -91.60:
        return "Meseta Comiteca, Chiapas"

    return "Chiapas, México"
