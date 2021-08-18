

class Clusters:
    def __init__(self, cluster_list, node_count):
        self._node_count = node_count
        self._c_list = cluster_list
        self._create_node_table()

    def _create_node_table(self):

        self._table = [0 for _ in range(0, self._node_count)]

        for cluster_index in range(0, len(self._c_list)):
            for node in self._c_list[cluster_index]:
                self._table[node] = cluster_index

    def matching_clusters(self, node1, node2):
        return self._table[node1] == self._table[node2]

    def get_cluster_index(self, node):
        return self._table[node]


    def __repr__(self):
        return str(self._c_list)

    @property
    def cluster_list(self):
        return self._c_list

