# LiteX TinyML Project Summary (Nexys4DDR)

This README is a concise project summary by implementation stages, with block diagrams and concrete matrix/compute details.

For full deep-dive documentation, see: `docs/PROJECT_ARCHITECTURE.md`.

---

## Stage 1 — Algorithm Definition

### 1) Exact Input Definition

- **Primary input tensor**: quantized image/feature map
- **Data type**: `INT8` (or `UINT8` in some quantization flows)
- **Typical example shape**: `32 x 32 x 3` (CIFAR-10 style)
- **Input size (example)**: `32*32*3 = 3072` elements = `3072 B` for 8-bit data
- **Storage location**: DDR2 main memory (`main_ram` region)

### 2) How many matrices/tensors are used

At inference time, each layer uses these matrix/tensor classes:

1. **Input activation tensor** (layer input)
2. **Weight matrix/tensor** (kernel/FC weights)
3. **Bias vector** (optional per output channel/neuron)
4. **Output activation tensor** (layer output)

For a standard CNN block, this repeats per layer, so the total number of matrices scales with number of layers.

### 3) Stage names and matrix role per stage

- **Stage A: Convolution / Linear Transform**
  - Input activation tensor + weight tensor (+ bias)
  - Produces pre-activation output tensor
- **Stage B: Non-linear Activation**
  - Applies ReLU/Sigmoid/Tanh on pre-activation tensor
  - Produces post-activation tensor
- **Stage C: Pooling / Reduction (optional per model)**
  - Downsamples activation tensor
- **Stage D: Fully Connected / Classifier**
  - Matrix-vector or matrix-matrix multiply
  - Produces logits/output vector

### 4) Matrix sizes (representative, from documented flow)

- **Input tensor**: `32 x 32 x 3`
- **Conv-1 weights**: `3 x 3 x 3 x 32` = `864` weights
- **Conv-1 output**: `32 x 32 x 32` = `32768` values (`32 KiB` at INT8)
- **Conv-2 output**: `32 x 32 x 32` = `32768` values
- **Pool output**: `16 x 16 x 32` = `8192` values
- **Later conv output example**: `16 x 16 x 64` = `16384` values
- **FC example**: `1024 x 128` weight matrix + `1024`-element input vector
- **Classifier output**: e.g., `10` logits

### Stage-1 block diagram

```text
Input Tensor (H x W x C)
        |
        v
+---------------------------+
| Convolution / MatMul      |
| (Weights + Bias)          |
+---------------------------+
        |
        v
+---------------------------+
| Non-linear Activation     |
| (ReLU / Sigmoid / Tanh)   |
+---------------------------+
        |
        v
+---------------------------+
| Pooling / Reduction       |
+---------------------------+
        |
        v
+---------------------------+
| FC / Classifier           |
+---------------------------+
        |
        v
Output logits / classes
```

---

## Stage 2 — CPU-Only (Without Accelerators)

### How CPU computes the algorithm

The VexRiscv CPU executes nested loops in software:

- Load activation and weights from DDR
- Perform multiply-accumulate (MAC) in scalar instructions
- Apply quantization/activation in software
- Store results back to DDR

Typical conv pseudocode pattern:

```c
for (oy = 0; oy < OH; oy++)
  for (ox = 0; ox < OW; ox++)
    for (oc = 0; oc < OC; oc++) {
      acc = bias[oc];
      for (ky = 0; ky < K; ky++)
        for (kx = 0; kx < K; kx++)
          for (ic = 0; ic < IC; ic++)
            acc += in[oy+ky][ox+kx][ic] * w[ky][kx][ic][oc];
      out[oy][ox][oc] = activate_and_quantize(acc);
    }
```

### CPU bottlenecks (data path + control path)

**Data path bottlenecks**

1. **DDR latency dominates**
   - Frequent load/store traffic for activations + weights
2. **Bandwidth pressure**
   - Repeated weight/input fetch with limited temporal reuse
3. **Low arithmetic parallelism**
   - Scalar MAC loop, limited SIMD in baseline path

**Control path bottlenecks**

1. **Deep nested-loop overhead**
   - Branch + index arithmetic per iteration
2. **High instruction count per output element**
   - Address calculation + memory ops + arithmetic + clamp/activation
3. **Synchronization/software orchestration overhead**
   - Especially around layer boundaries and tensor movement

### Stage-2 block diagram

```text
CPU (VexRiscv)
   |
   | software loops + scalar MAC
   v
Wishbone interconnect <-> DDR2 controller <-> DDR2 memory
   ^
   |
result write-back + next-layer read
```

---

## Stage 3 — Accelerators

This stage adds specialized hardware blocks to reduce CPU data/control bottlenecks.

### Accelerator A: LUT Activation Unit

**What it does**

- Replaces expensive non-linear calculations with lookup-table reads
- Supports ReLU/Sigmoid/Tanh style mappings in quantized domain

**How LUT tables are created**

- Precompute function offline (Python/tool flow)
- Quantize function output to target fixed-point/INT format
- Store into LUT memory mapped to accelerator CSR/data path

Example generation principle:

- ReLU: `y = max(0, x)`
- Sigmoid: `y = round( scale * (1 / (1 + exp(-x))) )`

### Accelerator B: Matrix Multiply Accelerator (MMA)

**What it does**

- Offloads INT8 matrix multiplication/MAC-heavy kernels
- Parallel MAC datapath processes multiple products per cycle

**How matrix multiplication is done**

- CPU writes matrix base addresses + dimensions to MMA CSRs
- MMA DMA/read engine fetches tiles/rows
- Parallel MAC array computes partial sums
- Accumulators and writeback unit store output matrix

### Accelerator C: ISA Extension + Dispatch

**What it does**

- Adds custom ISA path to trigger accelerators with low software overhead
- CPU issues custom op; decode logic routes to LUT/MMA control path

**How implemented in CPU path (conceptual)**

1. Decode custom opcode/funct fields
2. Map to accelerator ID and operation mode
3. Write command/args to accelerator CSR interface
4. Stall or wait-for-interrupt/poll completion
5. Resume pipeline with result/status

### Expected speedup

- **Activation stage**: typically large gain vs software non-linear loop
- **MatMul/Conv stage**: dominant acceleration source
- **System-level target**: multi-x speedup vs CPU-only baseline (commonly ~`4x` to `8x` class depending on DDR behavior and layer mix)

> Practical speedup depends on memory traffic and layer shapes; compute blocks accelerate MACs most, but DDR remains a system limiter.

### Stage-3 block diagram

```text
                  +----------------------+
                  |      VexRiscv CPU    |
                  |  + custom ISA decode |
                  +----------+-----------+
                             |
                             v
                    +----------------+
                    |  CSR/Dispatch  |
                    +---+--------+---+
                        |        |
          +-------------+        +----------------+
          v                                       v
+---------------------+                  +---------------------+
| LUT Activation Acc. |                  | Matrix Mul Acc.     |
| table lookup engine |                  | parallel MAC array  |
+----------+----------+                  +----------+----------+
           \                                      /
            \                                    /
             +---------- Wishbone/L2 -----------+
                             |
                             v
                         DDR2 memory
```

---

## End-to-end system block diagram

```text
+------------------------------------------------------------------+
|                    LiteX SoC (Nexys4DDR)                         |
|                                                                  |
|  +-----------+    +------------------+    +-------------------+  |
|  | VexRiscv  |<-->| Wishbone / CSR   |<-->| LiteDRAM DDR2 Ctrl |  |
|  | CPU       |    | Interconnect      |    +---------+---------+  |
|  +-----+-----+    +----+---------+----+              |            |
|        |               |         |                   |            |
|        |               |         |                   v            |
|        |               |   +-----+------+      +-----------+      |
|        |               |   | LUT Accel  |      | DDR2 SDRAM |      |
|        |               |   +------------+      +-----------+      |
|        |               |   +------------+                           |
|        +------------------>| MMA Accel  |                           |
|                            +------------+                           |
+------------------------------------------------------------------+
```

---

## Notes on traceability

- Full architecture and detailed rationale: `docs/PROJECT_ARCHITECTURE.md`
- Memory/resource context: `docs/MEMORY_CONFIG.md`
- Build/program flow: `docs/VIVADO_WINDOWS_BUILD.md`, `docs/PROGRAM_FPGA.md`
