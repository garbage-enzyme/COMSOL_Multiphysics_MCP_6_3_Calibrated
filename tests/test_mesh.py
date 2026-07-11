"""Unit tests for mesh helpers without a COMSOL client."""

from src.tools.mesh import get_mesh_info


class FakeFeatureList:
    def tags(self):
        return ["size", "ftet1"]


class FakeMesh:
    def label(self):
        return "Physics-controlled mesh"

    def feature(self):
        return FakeFeatureList()

    def getNumElem(self):
        return 18837

    def getNumVertex(self):
        return 4120


class FakeMeshList:
    def __init__(self, meshes):
        self.meshes = meshes

    def tags(self):
        return list(self.meshes)

    def get(self, tag):
        return self.meshes[tag]


class FakeComponent:
    def __init__(self, meshes):
        self.meshes = meshes

    def tag(self):
        return "comp1"

    def mesh(self):
        return FakeMeshList(self.meshes)


class FakeComponentList:
    def __init__(self, component):
        self.component = component

    def tags(self):
        return ["comp1"]

    def get(self, tag):
        return self.component


class FakeJava:
    def __init__(self, component):
        self.component_node = component

    def component(self, tag=None):
        if tag is None:
            return FakeComponentList(self.component_node)
        return self.component_node


class FakeModel:
    def __init__(self, meshes):
        self.java = FakeJava(FakeComponent(meshes))


class JavaStringLike:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value


class JavaTagFeatureList(FakeFeatureList):
    def tags(self):
        return [JavaStringLike("size"), JavaStringLike("ftet1")]


class JavaTagMesh(FakeMesh):
    def feature(self):
        return JavaTagFeatureList()


class JavaTagMeshList(FakeMeshList):
    def tags(self):
        return [JavaStringLike(tag) for tag in self.meshes]

    def get(self, tag):
        return self.meshes[str(tag)]


class JavaTagComponent(FakeComponent):
    def mesh(self):
        return JavaTagMeshList(self.meshes)


def test_get_mesh_info_uses_clientapi_counts():
    result = get_mesh_info(FakeModel({"mesh1": FakeMesh()}))

    assert result == {
        "success": True,
        "mesh": {
            "name": "mesh1",
            "component": "comp1",
            "features": ["size", "ftet1"],
            "label": "Physics-controlled mesh",
            "num_elements": 18837,
            "num_vertices": 4120,
        },
    }


def test_get_mesh_info_resolves_label():
    result = get_mesh_info(
        FakeModel({"mesh1": FakeMesh()}),
        mesh_name="Physics-controlled mesh",
    )

    assert result["success"] is True
    assert result["mesh"]["name"] == "mesh1"


def test_get_mesh_info_reports_available_tags():
    result = get_mesh_info(FakeModel({"mesh1": FakeMesh()}), mesh_name="missing")

    assert result["success"] is False
    assert "mesh1" in result["error"]


def test_get_mesh_info_normalizes_java_string_tags():
    model = FakeModel({"mesh1": JavaTagMesh()})
    model.java = FakeJava(JavaTagComponent({"mesh1": JavaTagMesh()}))

    result = get_mesh_info(model)

    assert result["success"] is True
    assert result["mesh"]["name"] == "mesh1"
    assert result["mesh"]["features"] == ["size", "ftet1"]
