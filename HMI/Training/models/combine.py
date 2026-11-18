import onnx, sys, ast
import onnxruntime as ort
from onnx import compose, helper
from onnxconverter_common import float16

outputPath = "MergedModel"

def merge_parallel_onnx_models(model_paths: list[str]) -> None:
    models = [onnx.load(path) for path in model_paths]
    if not models:
        raise ValueError("Provide at least one ONNX model path.")

    first_model = next(iter(models))
    shared_input = next(iter(first_model.graph.input))
    shared_input_name = shared_input.name

    all_nodes = []
    all_initializers = []
    all_sparse_initializers = []
    all_value_infos = []
    all_outputs = []
    merged_metadata = {}

    for idx, model in enumerate(models):
        prefix = f"m{idx}_"
        first_input = next(iter(model.graph.input))
        orig_input_name = first_input.name

        for prop in model.metadata_props:
            merged_metadata[f"{prefix}{prop.key}"] = prop.value

        prefixed = compose.add_prefix(model, prefix=prefix)
        prefixed_input_name = f"{prefix}{orig_input_name}"

        for node in prefixed.graph.node:
            for i, inp in enumerate(node.input):
                if inp == prefixed_input_name:
                    node.input[i] = shared_input_name

        all_nodes.extend(prefixed.graph.node)
        all_initializers.extend(prefixed.graph.initializer)
        all_sparse_initializers.extend(prefixed.graph.sparse_initializer)
        all_value_infos.extend(prefixed.graph.value_info)
        all_outputs.extend(prefixed.graph.output)

    all_names = []
    for i in range(len(models)):
        raw_names = merged_metadata.get(f"m{i}_names")
        if raw_names is not None:
            all_names.append(ast.literal_eval(raw_names))

    if all_names:
        merged_metadata["names"] = repr(all_names)

    merged_graph = helper.make_graph(
        nodes=all_nodes,
        name="merged_parallel_yolon",
        inputs=[shared_input],
        outputs=all_outputs,
        initializer=all_initializers,
        sparse_initializer=all_sparse_initializers,
        value_info=all_value_infos,
    )

    merged_model = helper.make_model(
        merged_graph,
        opset_imports=first_model.opset_import,
        ir_version=first_model.ir_version,
    )

    # Explicitly populate metadata_props using StringStringEntryProto
    del merged_model.metadata_props[:]
    for k, v in merged_metadata.items():
        entry = merged_model.metadata_props.add()
        entry.key = str(k)
        entry.value = str(v)

    onnx.checker.check_model(merged_model)
    modelFP16 = float16.convert_float_to_float16(
        merged_model,
        keep_io_types=True,
    )

    for node in modelFP16.graph.node:
        if node.op_type == "Cast" and "Resize_output_cast" in node.name:
            for attr in node.attribute:
                if attr.name == "to" and attr.i == onnx.TensorProto.FLOAT:
                    attr.i = TensorProto.FLOAT16
    del modelFP16.graph.value_info[:]


    onnx.save(merged_model, outputPath + "FP32.onnx")
    onnx.save(modelFP16, outputPath + "FP16.onnx")

# Example usage with 3 (or N) YOLOv8n models
merge_parallel_onnx_models(model_paths=sys.argv[1:])
