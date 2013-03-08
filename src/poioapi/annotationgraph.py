# -*- coding: utf-8 -*-
#
# Poio Tools for Linguists
#
# Copyright (C) 2009-2013 Poio Project
# Author: Peter Bouda <pbouda@cidles.eu>
# URL: <http://media.cidles.eu/poio/>
# For license information, see LICENSE.TXT

from __future__ import unicode_literals

import os.path
import codecs
import operator

from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring
import xml.etree.ElementTree as ET

import poioapi.io.elan
import poioapi.io.header
import poioapi.io.typecraft
from poioapi import data

from graf import GraphParser

class AnnotationGraph():

    def __init__(self, data_structure_type):
        self.data_structure_type = data_structure_type

        if data_structure_type is None:
            self.structure_type_handler = None
        elif isinstance(data_structure_type, data.DataStructureType):
            self.structure_type_handler = data_structure_type
        else:
            raise(
                data.DataStructureTypeNotSupportedError(
                    "Data structure type {0} not supported".format(
                        data_structure_type)))

        self.graf = None
        self.graf_basename = None

    def load_graph_from_graf(self, filepath):
        """Load the project annotation graph from a GrAF/XML file.

        Parameters
        ----------
        filepath : str
            The path to a GrAF/XML file.

        """
        parser = GraphParser()
        self.graf = parser.parse(filepath)
        (self.graf_basename, _) = os.path.splitext(os.path.abspath(filepath))

        # read the base data to get string for regions
        base_data_file = self.graf_basename + ".txt"
        try:
            with codecs.open(base_data_file, "r", "utf-8") as f:
                self.base_data = f.read()
        except:
            pass

    def root_nodes(self):
        """Retrieve the root nodes from the annotation graph. Root nodes are
        the nodes that have a label that is the root node of the data structure
        type as the root node. The root nodes are order by the "start" value
        of their region.

        Returns
        -------
        root_nodes : list of graf.Node
            Return root nodes of the graph.

        """
        res = list()
        base_tier_name =  self.structure_type_handler.flat_data_hierarchy[0]
        for (node_id, node) in self.graf.nodes.items():
            if node_id.startswith(base_tier_name):
                res.append(node)

        return sorted(res, key=lambda node: node.links[0][0].start)

    def nodes_for_tier(self, tier_name, parent_node = None):
        """Retreive all nodes for a given tier name. The parameter
        tier_name specifies the type if the neigbours. For example if
        the parent node is an utterance the tier name "word" specifies that
        all "word" nodes that are connected to the utterance node should
        be returned. The tier name must be a children of the parent node's
        type in the data hierarchy.

        Parameters
        ----------
        tier_name : str
            The label of the neighbour nodes to search.
        parent_node : graf.Node
            The ID of the node to start the search.

        Returns
        -------
        nodes : list of graf.Node

        """
        #node = self.graf.nodes[node_id]
        res = []
        if parent_node:
            for edge in parent_node.out_edges:
                target_node = edge.to_node
                if target_node.annotations.get_first().label == tier_name:
                    res.append(target_node)
        else:
            for target_node in self.graf.nodes:
                if target_node.annotations.get_first().label == tier_name:
                    res.append(target_node)
        return res

    def annotations_for_tier(self, tier_name, node):
        """Return all annotations of the given node that belong to the given
        tier name. The tier name is matched with the `label` of the
        annotations.

        Parameters
        ----------
        tier_name : str
            The label to search for in the annotations.
        node : graf.Node
            The node that has annotation to search.

        Returns
        -------
        annotations : list of graf.Annotation

        """
        res = []
        for a in node.annotations:
            if a.label == tier_name:
                res.append(a)

        return res

    def annotation_value_for_annotation(self, annotation):
        """Returns the annotation value for a given annotation.

        Parameters
        ----------
        annotation: graf.Annotation
            The annotation to get the value for.

        Returns
        -------
        annotation_value : str
            The annotation value.
        """
        return annotation.features.get_value("annotation_value")

    def as_html_table(self, filtered = False, full_html = True):
        """Return the graph as a HTML table.

        Parameters
        ----------
        filtered : bool
            Whether to us the filtered graph or the full graph.
        full_html: bool
            Whether to return a complete HTML page (i.e. with "<html>" etc.)
            or just the <table> element.

        Returns
        -------
        html = str
            The HTML for the GrAF graph.

        """
        html = ""
        if full_html:
            html = "<html><head><meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\" /></head><body>\n"

        for i, root_node in enumerate(self.root_nodes()):
            html += "<table>\n"

            table = [dict() for _ in range(len(
                self.structure_type_handler.flat_data_hierarchy))]

            self._node_as_table(
                root_node, self.structure_type_handler.data_hierarchy, table, 0)

            for j, row in enumerate(table):
                html += "<tr>\n"
                if j == 0:
                    html += "<td rowspan=\"{0}\" "\
                            "class=\"element_id\">{1}</td>\n".format(
                        len(self.structure_type_handler.flat_data_hierarchy), i)
                html += "<td class=\"ann_type\">{0}</td>".format(
                    self.structure_type_handler.flat_data_hierarchy[j])
                for _, column in sorted(row.items(), key=operator.itemgetter(0)):
                    html += "<td colspan=\"{0}\" class=\"{2}\">{1}</td>\n".format(
                        column[1], column[0],
                        self.structure_type_handler.flat_data_hierarchy[j])
                html += "</tr>\n"

            html += "</table>\n"

        if full_html:
            html += "</body></html>"

        f = open("test.html", "wb")
        f.write(html.encode("utf-8"))
        f.close()

        return html

    def _node_as_table(self, node, hierarchy, table, column):
        """Insert an element into a table.

        Parameters
        ----------
        node : array_like
            The root node to start the traversal.
        hierarchy: array_like
            An array with the data structure hierarchy.
        table : array_like
            The table to store the annotations to.
        column: int
            The current column number.

        Returns
        -------
        inserted : int
            Number of elements inserted.

        """

        inserted = 0

        for i, t in enumerate(hierarchy):

            if type(t) is list:
                node_list = self.nodes_for_tier(t[0], node)
                for i, n in enumerate(node_list):
                    inserted += self._node_as_table(
                        n, t, table, column + i + inserted)
                inserted = inserted + len(node_list) - 1
                merge_rows = [ r for r in hierarchy if type(r) is not list]
                for r in merge_rows:
                    row = self.structure_type_handler.flat_data_hierarchy.index(r)
                    if column in table[row]:
                        table[row][column] = (table[row][column][0], inserted + 1)
                    else:
                        table[row][column] = ("", inserted + 1)
            else:
                row = self.structure_type_handler.flat_data_hierarchy.index(t)

                a_list = self.annotations_for_tier(t, node)
                a = ""
                if len(a_list) > 0:
                    a = self.annotation_value_for_annotation(a_list[0])
                if a == "":
                    a = "&nbsp;"

                if column in table[row]:
                    table[row][column] = (a, table[row][column][1])
                else:
                    table[row][column] = (a, 1)

        return inserted

    def from_elan(self, elanfile):
        """This method generates a GrAF object
        from a Elan file.

        """

        elan = poioapi.io.elan.Parser(elanfile)

        # Create a GrAF object
        self.graf = elan.as_graf()

        self.data_structure_constraints = elan.data_structure_constraints

    def from_typecraft(self, typecraftfile):
        """This method generates a GrAF object
        from a Typecraft file.

        """

        typecraft = poioapi.io.typecraft.Parser(typecraftfile)

        # Create a GrAF object
        self.graf = typecraft.as_graf()

        # Gather all the information to generate the GrAF files
        self.basedirname = typecraft.basedirname
        self.filename = typecraft.filename
        self.filepath = typecraft.filepath
        self.xml_files_map = typecraft.xml_files_map

    def from_pickle(self):
        """This method generates a GrAF object
        from a pickle file.

        """

        pass

    def generate_graf_files(self, inputfile, outputfile):
        """This method will create the GrAF Xml files.
        But first is need to create the GrAF object in
        order to get the values.
        In some specific cases this method will also
        create a metafile that will gathered all the
        data information to recreate a file. Elan type
        is one of those specific files and this metafile
        will garante that the extra information from the
        files like the data structure hierarchy,
        the vocabulary, the media descriptor and etc,
        will be stored. The header file it's created too.

        """

        filename = os.path.abspath(outputfile)
        (basedirname, file_extension) = os.path.splitext(outputfile)
        header = poioapi.io.header.HeaderFile(basedirname)
        header.filename = os.path.splitext(filename)[0]
        header.primaryfile = os.path.basename(outputfile)
        header.dataType = 'text'

        for elements in self.graf.additional_information.items():
            file_name = elements[0]
            extension = file_name+".xml"
            filepath = basedirname+"-"+extension
            loc = os.path.basename(filepath)
            header.add_annotation(loc, file_name)
            file = open(filepath,'wb')
            element_tree = elements[1]
            doc = minidom.parseString(tostring(element_tree))
            file.write(doc.toprettyxml(indent='  ', encoding='utf-8'))
            file.close()

        header.create_header()

        if file_extension is ".eaf":
            self._generate_metafile(inputfile)

    def _generate_metafile(self, inputfile):
        """ This method will create a metafile
        from the original file.

        """

        (basedirname, _) = os.path.splitext(inputfile)

        tree = ET.parse(inputfile)
        root = tree.getroot()

        # Generate the metadata file
        element_tree = Element('metadata')

        header_tag = SubElement(element_tree, 'header')

        data_structure = SubElement(header_tag, 'data_structure')

        SubElement(data_structure, 'hierarchy').text =\
        str(['utterance'])

        tier_mapping = SubElement(header_tag,'tier_mapping')

        for values in self.data_structure_constraints.items():
            key = values[0]
            values = values[1]
            type = SubElement(tier_mapping,'type', {'name':key})
            for value in values:
                SubElement(type, 'tier').text = value

        file_tag = SubElement(element_tree, "file",
                {"data_type":'elan'})

        miscellaneous = SubElement(file_tag, "miscellaneous")

        # Add the root element
        SubElement(miscellaneous, root.tag, root.attrib)

        for child in root:
            parent = SubElement(miscellaneous, child.tag, child.attrib)
            for lower_child in child:
                if lower_child.tag != "ALIGNABLE_ANNOTATION" and\
                   lower_child.tag != "REF_ANNOTATION" and\
                   lower_child.tag != "ANNOTATION_VALUE" and\
                   lower_child.tag != "ANNOTATION":
                    child_element = SubElement(parent, lower_child.tag,
                        lower_child.attrib)
                    if not str(lower_child.text).isspace() or\
                       lower_child.text is not None:
                        child_element.text = lower_child.text

        filename = basedirname+"-extinfo.xml"
        file = open(filename,'wb')
        doc = minidom.parseString(tostring(element_tree))
        file.write(doc.toprettyxml(indent='  ', encoding='utf-8'))
        file.close()
