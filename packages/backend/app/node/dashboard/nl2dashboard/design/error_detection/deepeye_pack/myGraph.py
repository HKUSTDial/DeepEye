"""
This file defines the myGraph class.

myGraph represents a graph with node info and pairwise distances. It is used by the diversified_ranking
algorithm: after partial-order scores are computed, similarity is used to adjust scores, and getTopK
returns the top-K charts.
"""

from .view import Chart

class myGraph(object):
    def __init__(self,node_num):
        """
        Attributes:
            node_num(int): the number of nodes in the graph.
            nodes(list): the list of nodes in the graph.
            dis(list): a matrix storing the info of the graph.
            sim(list): a matrix storing the info of the graph, but the value of each element
                       is sim[i][j] = 1 / dis[i][j], used in getSim function.
        """
        self.node_num = 0
        self.nodes = []
        self.G = [[float('inf') for i in range(node_num)] for j in range(node_num)]
        self.dis = self.G[:]
        self.sim = [[0 for i in range(node_num)] for j in range(node_num)] # create a square matrix

    def getCost(self,node1,node2):
        """
        For node1 and node2, which represent two different views, return the cost of the two views.
        Here the cost is calculated according to the difference of two views. The more different of
        two views, the larger cost there will be.

        Args:
            node1(View), node2(View): Two different nodes.

        Returns:
            The cost two different nodes, calculated according to the different of the two nodes.
        """
        #markEditOps   ->   p5 (change chart type) and p4 (different aggregation)
        if node1.table.describe == node2.table.describe and node1.x_name == node2.x_name:
            if node1.y_name == node2.y_name and node1.chart == node2.chart:
                return 0.02
            elif node1.y_name == node2.y_name:
                if node1.chart == Chart.pie and node2.chart == Chart.bar:
                    return 0.03
                if node1.chart == Chart.pie and node2.chart == Chart.line:
                    return 0.02
                if node1.chart == Chart.pie and node2.chart == Chart.scatter:
                    return 0.04
                if node1.chart == Chart.bar and node2.chart == Chart.line:
                    return 0.04
                if node1.chart == Chart.bar and node2.chart == Chart.scatter:
                    return 0.02
                if node1.chart == Chart.line and node2.chart == Chart.scatter:
                    return 0.03
            elif node1.chart == node2.chart:
                if node1.y_name[0:3] == 'CNT' or node2.y_name[0:3] == 'CNT':
                    return 0.02
                t1,t2 = node1.y_name,node2.y_name
                if node1.y_name[0:3] == 'SUM' or node1.y_name[0:3] == 'AVG':
                    t1 = t1[4:-1]
                if node2.y_name[0:3] == 'SUM' or node2.y_name[0:3] == 'AVG':
                    t2 = t2[4:-1]
                if t1 == t2:
                    return 0.01
        #transformEditOps  ->    p3 (BIN)
        elif node1.table.describe == '' and node2.table.describe[0:3] == 'BIN' and node1.x_name == node2.x_name[0:len(node1.x_name)] and node1.y_name == node2.y_name[4:-1] and node1.chart == node2.chart:
            return 0.62
        elif node2.table.describe == '' and node1.table.describe[0:3] == 'BIN' and node2.x_name == node1.x_name[0:len(node2.x_name)] and node2.y_name == node1.y_name[4:-1] and node1.chart == node2.chart:
            return 0.62
        #encodingEditOps   ->   p1 (change x) and p2 (change y)
        elif node1.table.describe == node2.table.describe and node1.y_name == node2.y_name and node1.chart == node2.chart:   #change x
            return 4.45
        elif node1.table.describe == node2.table.describe and node1.x_name == node2.x_name and node1.chart == node2.chart:   #change y
            return 4.45
        elif node1.table.describe2 == node2.table.describe and node1.table.describe1[0:5] == 'GROUP' and node1.x_name == node2.x_name and node1.chart == node2.chart:  #add z
            t1, t2 = node1.y_name, node2.y_name
            if node1.y_name[0:3] == 'SUM' or node1.y_name[0:3] == 'AVG':
                t1 = t1[4:-1]
            if node2.y_name[0:3] == 'SUM' or node2.y_name[0:3] == 'AVG':
                t2 = t2[4:-1]
            if t1 == t2:
                return 4.22
        elif node2.table.describe2 == node1.table.describe and node2.table.describe1[0:5] == 'GROUP' and node1.x_name == node2.x_name and node1.chart == node2.chart:   #add z
            t1, t2 = node1.y_name, node2.y_name
            if node1.y_name[0:3] == 'SUM' or node1.y_name[0:3] == 'AVG':
                t1 = t1[4:-1]
            if node2.y_name[0:3] == 'SUM' or node2.y_name[0:3] == 'AVG':
                t2 = t2[4:-1]
            if t1 == t2:
                return 4.22
        return float('inf')


    def addNode(self,node):
        """
        Add a new node to the graph.

        Args:
            node(View): The new node to be added to the graph.
            
        Returns:
            None
            
        """
        self.nodes.append(node)
        for i in range(self.node_num):
            self.G[i][self.node_num] = self.G[self.node_num][i] = self.dis[i][self.node_num] = self.dis[self.node_num][i] = self.getCost(self.nodes[i], node)
        self.node_num += 1

    def getSim(self):
        """
        Get distance by Floyd algorithm and then get similarity. Here the similarity of two nodes i and j is
        defined as 1 / dis[i][j], where dis[i][j] is the shortest path of nodes i and j.

        Args:
            None
            
        Returns:
            None
            
        """
        # get dis by floyd
        for k in range(self.node_num):
            for i in range(self.node_num):
                for j in range(self.node_num):
                    if self.dis[i][j] > self.dis[i][k] + self.dis[k][j]:
                        self.dis[i][j] = self.dis[i][k] + self.dis[k][j]

        #get sim
        for i in range(self.node_num):
            for j in range(self.node_num):
                self.sim[i][j] = 1.0 / self.dis[i][j]


    def getTopK(self,K):
        """
        Get the charts of Top k scores

        Args:
            K(int): the number of results
            
        Returns:
            List of Top k results' index
            
        """
        score = 0
        result = []
        for k in range(K):
            max_id = -1
            max_delta_score = float('-inf')
            for i in range(self.node_num):
                if i in result:
                    continue
                delta_score = self.nodes[i].score
                for j in result:
                    delta_score -= 0.5 * (self.sim[i][j] * (self.nodes[i].score + self.nodes[j].score))
                if delta_score > max_delta_score:
                    max_delta_score = delta_score
                    max_id = i
            score = score + max_delta_score
            result.append(max_id)
        return result
