#!/usr/bin/env python3
"""
Converts public/models/dishes/chicken-biryani.glb into a valid Apple-compatible
USDZ (chicken-biryani.usdz) using Pixar's USD (pxr).

Reads the GLB generically: POSITION + NORMAL (+ optional TEXCOORD_0) accessors,
embedded PNG textures, and PBR baseColorTexture materials. Rebuilds the same
geometry + materials as a USD stage and archives with usdzip --arkitAsset.

Run: python3 scripts/glb-to-usdz.py
Output: public/models/dishes/chicken-biryani.usdz
"""
import io
import json
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

ROOT = Path(__file__).resolve().parent.parent
GLB = ROOT / "public/models/dishes/chicken-biryani.glb"
OUT = ROOT / "public/models/dishes/chicken-biryani.usdz"

COMPONENT_FLOAT = 5126
COMPONENT_UINT32 = 5125


def read_glb(path: Path):
    data = path.read_bytes()
    if data[:4] != b"glTF":
        raise ValueError("Not a GLB file")
    json_len = struct.unpack("<I", data[12:16])[0]
    gltf = json.loads(data[20 : 20 + json_len].rstrip(b" ").decode("utf-8"))
    bin_start = 20 + json_len + 8
    bin_data = data[bin_start:]
    return gltf, bin_data


def read_accessor(gltf, bin_data, acc_idx):
    acc = gltf["accessors"][acc_idx]
    bv = gltf["bufferViews"][acc["bufferView"]]
    comp = acc["componentType"]
    count = acc["count"]
    type_name = acc["type"]
    n_comp = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[type_name]
    fmt = {COMPONENT_FLOAT: "f", COMPONENT_UINT32: "I"}[comp]
    size = struct.calcsize("<" + fmt)
    stride = bv.get("byteStride", size * n_comp)
    off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    values = []
    for i in range(count):
        base = off + i * stride
        item = struct.unpack_from("<" + fmt * n_comp, bin_data, base)
        values.append(item if n_comp > 1 else item[0])
    return values


def extract_texture(gltf, bin_data, tex_idx):
    """Return RGBA Pillow image for a glTF texture index (embedded PNG)."""
    tex = gltf["textures"][tex_idx]
    img = gltf["images"][tex["source"]]
    bv = gltf["bufferViews"][img["bufferView"]]
    blob = bin_data[bv["byteOffset"] : bv["byteOffset"] + bv["byteLength"]]
    return Image.open(io.BytesIO(blob)).convert("RGBA")


def build_usd(gltf, bin_data, out_usda: Path):
    stage = Usd.Stage.CreateNew(str(out_usda))
    stage.SetDefaultPrim(stage.DefinePrim("/Biryani", "Xform"))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = stage.GetDefaultPrim()

    # Extract textures to sibling PNG files (usdzip packages them).
    texture_paths = {}
    for ti in range(len(gltf.get("textures", []))):
        pil = extract_texture(gltf, bin_data, ti)
        p = out_usda.parent / f"tex_{ti}.png"
        pil.save(p)
        texture_paths[ti] = str(p)

    for node_idx in gltf["scenes"][gltf["scene"]]["nodes"]:
        node = gltf["nodes"][node_idx]
        mesh = gltf["meshes"][node["mesh"]]
        name = node.get("name", f"mesh{node_idx}")
        for pi, prim in enumerate(mesh["primitives"]):
            positions = read_accessor(gltf, bin_data, prim["attributes"]["POSITION"])
            normals = read_accessor(gltf, bin_data, prim["attributes"]["NORMAL"])
            uvs = read_accessor(gltf, bin_data, prim["attributes"]["TEXCOORD_0"]) if "TEXCOORD_0" in prim["attributes"] else None
            indices = read_accessor(gltf, bin_data, prim["indices"])

            mesh_path = f"/Biryani/{name}" if len(mesh["primitives"]) == 1 else f"/Biryani/{name}_{pi}"
            usd_mesh = UsdGeom.Mesh.Define(stage, mesh_path)
            usd_mesh.CreatePointsAttr(list(Gf.Vec3f(*p) for p in positions))
            usd_mesh.CreateNormalsAttr(list(Gf.Vec3f(*n) for n in normals))
            usd_mesh.CreateFaceVertexIndicesAttr([int(i) for i in indices])
            usd_mesh.CreateFaceVertexCountsAttr([3] * (len(indices) // 3))
            usd_mesh.CreateSubdivisionSchemeAttr("none")
            if uvs:
                UsdGeom.PrimvarsAPI(usd_mesh).CreatePrimvar(
                    "st", Sdf.ValueTypeNames.TexCoord2fArray, UsdGeom.Tokens.varying
                ).Set(list(Gf.Vec2f(u[0], 1 - u[1]) for u in uvs))

            mat_idx = prim.get("material")
            if mat_idx is not None:
                gmat = gltf["materials"][mat_idx]
                mat_name = gmat.get("name", f"mat_{mat_idx}")
                mat = UsdShade.Material.Define(stage, f"/Biryani/{name}/mat_{mat_name}")
                pbr = UsdShade.Shader.Define(stage, f"/Biryani/{name}/mat_{mat_name}/PBRShader")
                pbr.CreateIdAttr("UsdPreviewSurface")

                pbr_meta = gmat.get("pbrMetallicRoughness", {})
                bcf = pbr_meta.get("baseColorFactor", [1, 1, 1, 1])
                pbr.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(
                    Gf.Vec3f(bcf[0], bcf[1], bcf[2])
                )
                pbr.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(
                    bcf[3] if len(bcf) > 3 else 1.0
                )
                pbr.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(
                    pbr_meta.get("metallicFactor", 0.0)
                )
                pbr.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(
                    pbr_meta.get("roughnessFactor", 1.0)
                )

                if "baseColorTexture" in pbr_meta and uvs:
                    ti = pbr_meta["baseColorTexture"]["index"]
                    tex_prim = UsdShade.Shader.Define(
                        stage, f"/Biryani/{name}/mat_{mat_name}/diffuseTex"
                    )
                    tex_prim.CreateIdAttr("UsdUVTexture")
                    tex_prim.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(
                        texture_paths[ti]
                    )
                    # Connect the texture's st input to the mesh primvar's
                    # "result" output (UsdUVTexture reads via st->result).
                    st_attr = UsdGeom.PrimvarsAPI(usd_mesh).GetPrimvar("st").GetAttr()
                    pv = UsdShade.ConnectableAPI(st_attr.GetPrim())
                    tex_prim.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(
                        pv, "primvars:st"
                    )
                    pbr.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
                        tex_prim.ConnectableAPI(), "rgb"
                    )

                mat.CreateSurfaceOutput().ConnectToSource(pbr.ConnectableAPI(), "surface")
                binding = UsdShade.MaterialBindingAPI.Apply(usd_mesh.GetPrim())
                binding.Bind(mat, UsdShade.Tokens.weakerThanDescendants)

    stage.GetRootLayer().Save()
    return stage


def main():
    gltf, bin_data = read_glb(GLB)
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        usda_path = tmpdir / "model.usda"
        build_usd(gltf, bin_data, usda_path)
        result = subprocess.run(
            ["usdzip", str(OUT), "--arkitAsset", str(usda_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            sys.stderr.write(result.stderr)
            raise SystemExit(f"usdzip failed: {result.returncode}")

    size = OUT.stat().st_size if OUT.exists() else 0
    print(f"wrote {OUT} ({size} bytes)")


if __name__ == "__main__":
    main()
