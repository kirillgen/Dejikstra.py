import osmium
import tkinter
import tkintermapview
from geopy.distance import geodesic


class CounterHandler(osmium.SimpleHandler):
    def __init__(self, way_type):
        super().__init__()
        # osmium.SimpleHandler.__init__(self)
        self.type_of_way = way_type
        self.nodes = {}
        self.ways = {}
        self.graph = {}
        self.distances = {}

    def node(self, n):
        lat = n.location.lat
        lon = n.location.lon
        self.nodes[str(n.id)] = (lat, lon)

    # метод для парсинга путей из файла
    def way(self, w):
        way_id = w.id
        nodes_in_way = [node.ref for node in w.nodes]

        tags = []
        if w.tags:
            tags = [{'k': tag.k, 'v': tag.v} for tag in w.tags]

        highway_by_car = {'track', 'path', 'residential', 'primary', 'secondary', 'unclassified', 'tertiary', 'service',
                          'driveway', 'motorway', 'trunk', 'parking_aisle'}

        highway_by_walk = {'service', 'pedestrian', 'unclassified', 'footway', 'track', 'path', 'steps', 'cycleway',
                           'parking_aisle', 'bridleway', 'residential', 'crossing'}

        if self.type_of_way == 'car':
            relevant_tags = highway_by_car
        elif self.type_of_way == 'walking':
            relevant_tags = highway_by_walk
        else:
            raise ValueError("Неизвестный тип движения")

        if not any(tag['k'] == 'highway' and tag['v'] in relevant_tags for tag in tags):
            return

        has_building_tag = any(tag['k'] == 'building' for tag in tags)
        if has_building_tag:
            # Если ключ 'building' найден, пропускаем этот путь
            return

        self.ways[way_id] = {'id': way_id, 'nodes': nodes_in_way, 'tags': tags}

    def calculate_distance(self, node1, node2):
        """Вычисляет расстояние между двумя узлами с использованием формулы гаверсинуса."""
        lat1, lon1 = self.nodes[str(node1)]
        lat2, lon2 = self.nodes[str(node2)]
        return geodesic((lat1, lon1), (lat2, lon2)).kilometers

    def build_graph(self):
        all_nodes = []
        for way_data in self.ways.values():
            all_nodes.extend(way_data['nodes'])

        self.graph = {node: [] for node in all_nodes}
        self.distances = {}  # Инициализируем словарь для расстояний

        for way_data in self.ways.values():
            nodes_in_way = way_data['nodes']
            for i in range(len(nodes_in_way) - 1):
                if nodes_in_way[i + 1] not in self.graph[nodes_in_way[i]]:
                    self.graph[nodes_in_way[i]].append(nodes_in_way[i + 1])
                    self.graph[nodes_in_way[i + 1]].append(nodes_in_way[i])
                    # Вычисляем расстояние между узлами и сохраняем его
                    distance = self.calculate_distance(nodes_in_way[i], nodes_in_way[i + 1])
                    self.distances[nodes_in_way[i]] = self.distances.get(nodes_in_way[i], {}) | {
                        nodes_in_way[i + 1]: distance}
                    self.distances[nodes_in_way[i + 1]] = self.distances.get(nodes_in_way[i + 1], {}) | {
                        nodes_in_way[i]: distance}  # Обратное расстояние


def shortest_path(distance_graph: dict, start_vertex: int, end_vertex: int):
    if start_vertex not in distance_graph or end_vertex not in distance_graph:
        return f'{start_vertex} и {end_vertex} не находятся в БД карты.'

    visited = set()
    distances = {elem: float('inf') for elem in distance_graph}
    distances[start_vertex] = 0
    paths = {start_vertex: [start_vertex]}

    while True:

        cur_vertex = min((v for v in distance_graph if v not in visited), key=lambda v: distances[v])

        if cur_vertex == end_vertex:
            return distances[end_vertex], paths[end_vertex]
        visited.add(cur_vertex)

        for neighbor, dist in distance_graph[cur_vertex].items():
            if neighbor in visited:
                continue
            new_distance = distances[cur_vertex] + dist
            if new_distance < distances[neighbor]:
                distances[neighbor] = new_distance
                paths[neighbor] = paths[cur_vertex] + [neighbor]


if __name__ == '__main__':
    start_node = 1843227098
    target_node = 3048099426
    type_of_way = 'car'  # 'walking' / 'car'

    h = CounterHandler(type_of_way)

    # Лучше использовать.pbf формат (более свежая версия)
    h.apply_file("Map/liechtenstein-latest.osm.pbf")

    h.build_graph()

    distance, short_path, *_ = shortest_path(h.distances, 442535874, 995356803)
    print(f"Общее расстояние: {distance}\nКратчайший путь: {short_path}")

    wayrepr = [h.nodes[str(node)] for node in short_path]
    print(f"Список для построения пути между двумя точками: {wayrepr}")

    # Работа с картой
    root_window = tkinter.Tk()
    root_window.geometry(f"{1920}x{1080}")
    root_window.title("Map Testing")

    map_widget = tkintermapview.TkinterMapView(root_window, width=1920, height=1080, corner_radius=0)
    map_widget.place(relx=0.5, rely=0.5, anchor=tkinter.CENTER)
    map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga")

    map_widget.set_position(h.nodes[str(start_node)][0], h.nodes[str(start_node)][1])

    map_widget.set_zoom(14)

    map_widget.set_path(wayrepr)

    map_widget.mainloop()
