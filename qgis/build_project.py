from __future__ import annotations

import os
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
QGIS_PREFIX = r"C:\Program Files\QGIS 3.44.11"


def bootstrap_qgis() -> None:
    os.environ.setdefault("QGIS_PREFIX_PATH", QGIS_PREFIX)
    sys.path.append(str(Path(QGIS_PREFIX) / "apps" / "qgis-ltr" / "python"))


def main() -> None:
    bootstrap_qgis()

    from qgis.core import (
        QgsApplication,
        QgsCoordinateReferenceSystem,
        QgsDataSourceUri,
        QgsFillSymbol,
        QgsGraduatedSymbolRenderer,
        QgsLayoutExporter,
        QgsLayoutItemLabel,
        QgsLayoutItemLegend,
        QgsLayoutItemMap,
        QgsLayoutItemPicture,
        QgsLayoutItemScaleBar,
        QgsLayoutPoint,
        QgsLayoutSize,
        QgsLineSymbol,
        QgsMarkerSymbol,
        QgsPrintLayout,
        QgsProject,
        QgsRendererRange,
        QgsSingleSymbolRenderer,
        QgsUnitTypes,
        QgsVectorLayer,
    )

    app = QgsApplication([], False)
    app.initQgis()

    project = QgsProject.instance()
    project.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))

    def uri_for(table: str, geom: str = "geom") -> str:
        uri = QgsDataSourceUri()
        uri.setConnection("localhost", "5764", "transit_accessibility", "postgres", "admin")
        uri.setDataSource("public", table, geom)
        return uri.uri(False)

    layer_specs = [
        ("study_area", "Study Area"),
        ("neighborhood_accessibility_map", "Accessibility Scores"),
        ("transit_routes", "Transit Routes"),
        ("transit_stops", "Transit Stops"),
        ("sidewalks", "Sidewalks"),
        ("schools", "Schools"),
        ("hospitals", "Hospitals"),
    ]

    layers = {}
    for table, name in layer_specs:
        layer = QgsVectorLayer(uri_for(table), name, "postgres")
        if not layer.isValid():
            print(f"Skipping invalid layer: {table}")
            continue
        project.addMapLayer(layer)
        layers[table] = layer

    if "study_area" in layers:
        symbol = QgsFillSymbol.createSimple({
            "color": "255,255,255,0",
            "outline_color": "80,80,80",
            "outline_width": "0.25",
        })
        layers["study_area"].setRenderer(QgsSingleSymbolRenderer(symbol))

    if "transit_routes" in layers:
        symbol = QgsLineSymbol.createSimple({"color": "86,150,63", "width": "0.45"})
        layers["transit_routes"].setRenderer(QgsSingleSymbolRenderer(symbol))

    if "sidewalks" in layers:
        symbol = QgsLineSymbol.createSimple({"color": "210,64,46", "width": "0.18"})
        layers["sidewalks"].setRenderer(QgsSingleSymbolRenderer(symbol))

    if "transit_stops" in layers:
        symbol = QgsMarkerSymbol.createSimple({"name": "circle", "color": "0,90,181", "size": "2.8"})
        layers["transit_stops"].setRenderer(QgsSingleSymbolRenderer(symbol))

    if "schools" in layers:
        symbol = QgsMarkerSymbol.createSimple({"name": "diamond", "color": "215,84,132", "size": "3.2"})
        layers["schools"].setRenderer(QgsSingleSymbolRenderer(symbol))

    if "hospitals" in layers:
        symbol = QgsMarkerSymbol.createSimple({"name": "square", "color": "130,98,171", "size": "3.2"})
        layers["hospitals"].setRenderer(QgsSingleSymbolRenderer(symbol))

    if "neighborhood_accessibility_map" in layers:
        ranges = [
            QgsRendererRange(0, 20, QgsFillSymbol.createSimple({"color": "153,0,13,180", "outline_color": "90,90,90"}), "0-20"),
            QgsRendererRange(20, 40, QgsFillSymbol.createSimple({"color": "252,141,89,180", "outline_color": "90,90,90"}), "20-40"),
            QgsRendererRange(40, 60, QgsFillSymbol.createSimple({"color": "255,255,191,180", "outline_color": "90,90,90"}), "40-60"),
            QgsRendererRange(60, 80, QgsFillSymbol.createSimple({"color": "145,207,96,180", "outline_color": "90,90,90"}), "60-80"),
            QgsRendererRange(80, 100, QgsFillSymbol.createSimple({"color": "26,152,80,180", "outline_color": "90,90,90"}), "80-100"),
        ]
        renderer = QgsGraduatedSymbolRenderer("accessibility_score", ranges)
        layers["neighborhood_accessibility_map"].setRenderer(renderer)

    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName("Transit Accessibility Map")
    project.layoutManager().addLayout(layout)

    map_item = QgsLayoutItemMap(layout)
    map_item.attemptMove(QgsLayoutPoint(8, 18, QgsUnitTypes.LayoutMillimeters))
    map_item.attemptResize(QgsLayoutSize(240, 165, QgsUnitTypes.LayoutMillimeters))
    if layers:
        extent = next(iter(layers.values())).extent()
        for layer in layers.values():
            extent.combineExtentWith(layer.extent())
        map_item.setExtent(extent)
    layout.addLayoutItem(map_item)

    title = QgsLayoutItemLabel(layout)
    title.setText("Transit Accessibility and Spatial Equity")
    title.attemptMove(QgsLayoutPoint(8, 6, QgsUnitTypes.LayoutMillimeters))
    title.attemptResize(QgsLayoutSize(180, 10, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(title)

    legend = QgsLayoutItemLegend(layout)
    legend.setLinkedMap(map_item)
    legend.attemptMove(QgsLayoutPoint(252, 18, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(legend)

    north_arrow = QgsLayoutItemPicture(layout)
    north_arrow.setPicturePath(str(Path(QGIS_PREFIX) / "apps" / "qgis-ltr" / "svg" / "arrows" / "NorthArrow_02.svg"))
    north_arrow.attemptMove(QgsLayoutPoint(252, 152, QgsUnitTypes.LayoutMillimeters))
    north_arrow.attemptResize(QgsLayoutSize(18, 18, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(north_arrow)

    scale = QgsLayoutItemScaleBar(layout)
    scale.setStyle("Single Box")
    scale.setLinkedMap(map_item)
    scale.applyDefaultSize()
    scale.attemptMove(QgsLayoutPoint(8, 186, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(scale)

    output_dir = PROJECT_ROOT / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    for output_name in ("transit_accessibility_map.pdf", "transit_accessibility_map.png"):
        output_path = output_dir / output_name
        if output_path.exists():
            output_path.unlink()
    exporter = QgsLayoutExporter(layout)
    exporter.exportToPdf(str(output_dir / "transit_accessibility_map.pdf"), QgsLayoutExporter.PdfExportSettings())
    exporter.exportToImage(str(output_dir / "transit_accessibility_map.png"), QgsLayoutExporter.ImageExportSettings())
    project.write(str(PROJECT_ROOT / "qgis" / "transit_accessibility.qgz"))

    app.exitQgis()


if __name__ == "__main__":
    main()
