# LiteX TinyML SoC: Project Architecture & Implementation Guide

**Document Version**: 1.0  
**Last Updated**: April 13, 2026  
**Project**: LiteX RISC-V SoC with TinyML Accelerators on Nexys4 DDR FPGA

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Stage 1: Algorithm Specification](#stage-1-algorithm-specification)
3. [Stage 2: CPU without Accelerators](#stage-2-cpu-without-accelerators)
4. [Stage 3: Hardware Accelerators](#stage-3-hardware-accelerators)
5. [System Architecture Block Diagrams](#system-architecture-block-diagrams)
6. [Performance Characteristics](#performance-characteristics)
7. [Build and Deployment](#build-and-deployment)

---

## Project Overview

### Vision
This project implements a complete TinyML inference pipeline on an FPGA-based SoC, starting with a pure CPU baseline and progressively adding specialized hardware accelerators for matrix operations, non-linear activations, and memory optimization.

### Hardware Platform
- **FPGA**: Xilinx Artix-7 (XC7A100T) on Digilent Nexys4 DDR board
- **CPU**: VexRiscv (32-bit RISC-V)
- **Memory**: 128 MB DDR2 SDRAM + 128 KiB on-chip ROM + 128 KiB L2 cache
- **System Clock**: 50 MHz (lowered from 100 MHz for DDR2 stability)
- **Interface**: UART (115200 baud) for debugging and control

### Development Stack
- **HDL Framework**: LiteX (Python-based hardware abstraction)
- **Simulation**: Migen (hardware description DSL)
- **CPU**: VexRiscv (open-source RISC-V implementation)
- **Memory Controller**: LiteDRAM (DDR2 PHY and controller)
- **Build System**: Python scripts + Vivado (Windows) for synthesis

---

## Stage 1: Algorithm Specification

### TinyML Model: Neural Network Inference Pipeline

This project implements **inference** for a quantized convolutional neural network (CNN) optimized for embedded systems.

#### Input Specification

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Input Data Type** | INT8 or UINT8 | Quantized activations |
| **Input Dimensions** | Variable (e.g., 224×224×3) | Height × Width × Channels |
| **Input Range** | [0, 255] or [-128, 127] | Depends on quantization scheme |
| **Input Memory** | Stored in DDR2 @ 0x80000000 | Pre-loaded from external source |

**Example Input Format (CIFAR-10):**
```
Shape: 32 × 32 × 3 (32x32 pixel RGB image)
Size: 32 × 32 × 3 = 3,072 bytes
Stored as: flat array in row-major order
```

#### Network Architecture: Three-Stage Pipeline

The typical TinyML model consists of three main computational stages:

```
┌─────────────────────────────────────────────────────────────────┐
│                    INPUT (224x224x3 or 32x32x3)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                ┌────────────▼──────────────┐
                │    CONVOLUTION STAGE      │  (2-8 layers)
                │  - Conv2D (3x3/5x5/7x7)  │
                │  - Batch Norm (fused)     │
                │  - ReLU (clipped activation) │
                └────────────────────────────┘
                             │
                ┌────────────▼──────────────┐
                │   POOLING & REDUCTION    │
                │  - MaxPool 2x2/AvgPool   │
                │  - Optional: Depthwise Conv │
                └────────────────────────────┘
                             │
                ┌────────────▼──────────────┐
                │   FULLY-CONNECTED STAGE  │  (1-3 layers)
                │  - Matrix Multiply       │
                │  - Add Bias              │
                │  - Activation (ReLU/Linear) │
                └────────────────────────────┘
                             │
                ┌────────────▼──────────────┐
                │    OUTPUT (Logits)       │
                │  Shape: Num_Classes      │
                └────────────────────────────┘
```

#### Matrix Specifications

##### **Stage 1: Convolution Matrices**

**Convolution Kernel (Conv2D)**
- **Type**: INT8 weights (fixed-point quantized)
- **Kernel Size**: 3×3, 5×5, or 7×7
- **Number of Filters**: 8 to 128 per layer
- **Input Channels**: Varies per layer (3 for first layer, 8-128 for others)
- **Output Channels**: 8 to 128

**Example: First Conv Layer**
```
Input:  H=32, W=32, Cin=3
Kernel: 3×3×3 = 27 weights per filter
Filters: 32 filters
Total Weights: 3×3×3×32 = 864 bytes per layer

Computation per output pixel:
  - 27 multiplications (3×3×3)
  - 26 accumulations
  - ~1 byte quantization/dequant overhead
```

**Activation Maps (Intermediate Tensors)**
- **Data Type**: INT8 or UINT8
- **Shape**: Height × Width × Channels
- **Storage**: DDR2 SDRAM (organized as row-major flat arrays)

---

**Example Layer Chain (CIFAR-10 Model)**:
```
Layer 1: Conv 3×3, 32 filters → Output: 32×32×32 = 32 KB
Layer 2: Conv 3×3, 32 filters → Output: 32×32×32 = 32 KB
Layer 3: MaxPool 2×2          → Output: 16×16×32 = 16 KB
Layer 4: Conv 3×3, 64 filters → Output: 16×16×64 = 16 KB
...
FC Layer: 1024→128            → Output: 128 bytes
Output Layer: 128→10          → Output: 10 bytes (class logits)
```

##### **Stage 2: Pooling Operations**

**Max Pooling**
- **Kernel Size**: 2×2 (typical)
- **Stride**: 2
- **Operation**: Select maximum value from 4 pixels
- **Data Type**: INT8
- **Output Size**: Halves both dimensions

**Average Pooling** (less common in TinyML)
- Same kernel/stride structure
- Operation: Sum 4 pixels + divide by 4 (with rounding)

##### **Stage 3: Fully-Connected Matrices**

**Weight Matrix (Dense/FC Layer)**
- **Data Type**: INT8 weights
- **Dimensions**: [Input_Neurons, Output_Neurons]
- **Example**: 1024×128 matrix = 131,072 bytes

**Bias Vector**
- **Data Type**: INT32 (accumulator result)
- **Dimensions**: [Output_Neurons]
- **Example**: 128-element vector = 512 bytes

**Computation per Output Neuron**:
```
output[j] = sum(input[i] * weight[i][j] for i in 0..Input_Neurons) + bias[j]
          = sum of Input_Neurons multiplications + 1 addition
          = 1024 MAC operations per output neuron
```

#### Quantization Scheme

**INT8 Quantization Parameters**:
```
For each tensor:
  - Scale factor: float32 (typically 0.001 to 0.1)
  - Zero-point: int8 offset (typically 0 or 128)
  
Dequantization formula:
  float_value = scale * (quantized_value - zero_point)
```

**Why INT8?**
- Reduces memory bandwidth (4× less than FP32)
- Enables efficient 8-bit arithmetic in FPGA
- Maintains acceptable accuracy for classification tasks
- Models typically pre-quantized using TensorFlow Lite or ONNX quantization tools

---

## Stage 2: CPU without Accelerators

### Architecture Overview

The VexRiscv CPU executes the entire TinyML algorithm using standard RISC-V instructions, with no hardware acceleration.

```
┌──────────────────────────────────────────────────────────────┐
│                    VexRiscv RISC-V CPU                       │
│                      (50 MHz, 32-bit)                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Fetch Unit  │───▶│ Decode Unit  │───▶│ Execute Unit │  │
│  │ (I-Cache)    │    │              │    │   (ALU/MUL)  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│        16 KiB             Standard             Standard      │
│                          RISC-V Decoder        RV32I, M    │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │            Register File (32 × 32-bit)                 │ │
│  │     x0(zero), x1(ra), ... x31(t6)                      │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────┐       ┌──────────────────────────┐  │
│  │   Data Cache       │       │   Load/Store Unit        │  │
│  │    (16 KiB)        │◀──────│ (to DDR2 + L2 Cache)     │  │
│  └────────────────────┘       └──────────────────────────┘  │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### ISA & Instruction Usage

**Supported Instruction Sets**:
- **RV32I**: Base integer instruction set (add, sub, ld, st, beq, etc.)
- **RV32M**: Multiply/Divide extension (mul, mulh, div, rem)

**Key Instructions for ML Inference**:

| Instruction | Format | Purpose | Latency |
|-------------|--------|---------|---------|
| `lw` | Load Word | Fetch INT8 from memory | 1-3 cycles (cache miss: 100+ cycles) |
| `sw` | Store Word | Write results to DDR2 | 1 cycle + DDR latency |
| `lb` | Load Byte | Fetch INT8 value | 1-3 cycles |
| `mul` | Multiply | INT32 = INT8 × INT8 | 2-3 cycles |
| `add`/`addi` | Add | Accumulate results | 1 cycle |
| `beq` | Branch Equal | Loop control | 1 cycle (no stall if predicted) |

### Data Path & Memory Hierarchy

**Memory Bandwidth Chain**:
```
CPU Registers (unlimited, 0 cycle latency)
    ↓
I-Cache/D-Cache (16 KiB each, 1-3 cycle hit latency)
    ↓
L2 Cache (128 KiB, 3-5 cycle hit latency)
    ↓
DDR2 SDRAM (128 MB, 50-200 cycle latency depending on page hit/miss)
```

**Example Memory Access Pattern (Convolution)**:
```
for each output pixel (h, w):
    for each filter (f):
        for each input channel (c):
            for ky in [0, 2]:              // kernel height
                for kx in [0, 2]:          // kernel width
                    load input[h+ky][w+kx][c]       // 1-3 cycles
                    load weight[ky][kx][c][f]       // 1-3 cycles
                    multiply                        // 2-3 cycles
                    accumulate                      // 1 cycle
```

### Bottleneck Analysis

#### **Data Path Bottlenecks**

1. **Memory Latency Bottleneck** (PRIMARY)
   - **Problem**: DDR2 access latency = 50-200 cycles
   - **Symptom**: CPU stalls waiting for memory
   - **Impact**: ~80-90% of execution time spent waiting for data
   - **Example**: Loading a 32×32 weight matrix requires:
     - Sequential loads: 1024 × 50-100 cycles = 50K-100K cycles
     - At 50 MHz: 1-2 ms per layer
   
   **Workaround**: L2 cache provides ~128 KiB local storage, but insufficient for large weight matrices

2. **Memory Bandwidth Bottleneck** (SECONDARY)
   - **Problem**: Each byte requires a separate memory transaction
   - **Calculation**: 
     - CIFAR-10 model ~300 KB weights + activations
     - Each memory access: 32-bit word (4 bytes)
     - Total transactions: 75,000 transactions
     - At 50 MHz with 100 cycle latency: 7.5M cycles ~150 ms
   
   **Root Cause**: Single-core sequential access pattern

3. **Arithmetic Bottleneck** (TERTIARY, less severe)
   - **Problem**: 1 multiply per cycle, but data not ready
   - **Example**: 
     - Convolution layer: 1M MAC operations
     - At 1 MAC/cycle @ 50 MHz: 20 ms
     - But waiting for data dominates
   
   **Mitigation**: Multiply unit is rarely the critical path due to memory stalls

#### **Control Path Bottlenecks**

1. **Loop Overhead**
   - Each convolution layer has 4-5 nested loops
   - Branch mispredictions: ~2% (modern VexRiscv has branch prediction)
   - Impact: Minor compared to memory latency

2. **Quantization/Dequantization Overhead**
   - Every 1000 operations requires INT8↔FP32 conversion
   - ~5-10 instructions per conversion
   - Impact: ~0.5-1% of total time

3. **Conditional Activation Functions** (ReLU, Clipping)
   - Simple comparison + conditional move
   - ~3 instructions per value
   - Impact: ~0.1-0.3% overhead

### Performance Characteristics

**Theoretical vs. Practical Performance**

**CIFAR-10 Classification (32×32 RGB input → 10 classes)**

```
Theoretical Maximum (Peak): 50 MHz × 1 MAC/cycle = 50 MMAC/s = 0.05 GMAC/s

Actual Model Execution (with stalls):
  Layer 1: Conv 3×3, 32 filters
    - Operations: (30×30) × 9 × 32 = 259,200 MACs
    - Data accesses: 1024 weights + 3072 input + 28800 output = 32,896 reads
    - Expected: 259,200 / 50M = 5.2 ms (ideal)
    - Actual: ~100-150 ms (19-28× slower due to memory latency)

  Total Model Time (5 layers): 500-750 ms
  
End-to-End Latency: 500 ms - 1 second
Throughput: 1-2 inference/second
```

**Bottleneck Breakdown**:
- Memory Latency: 85-90% of execution time
- Arithmetic Operations: 5-10%
- Branch/Control: 2-3%
- Quantization Overhead: 1-2%

### Baseline Code Structure

**Pseudocode for Conv2D (CPU Only)**:
```c
// Convolution: Output[h][w][f] = sum over spatial kernel of Input[h+ky][w+kx][c] * Kernel[ky][kx][c][f]

void conv2d_baseline(
    int8_t *input,      // [H][W][C_in]  - starts at 0x80000000
    int8_t *kernel,     // [3][3][C_in][C_out]
    int32_t *output,    // [H_out][W_out][C_out]  - temporary accumulator
    int height, int width, int c_in, int c_out,
    int stride, int padding
) {
    // Loop 1: Output spatial dimensions
    for (int h = 0; h < height; h += stride) {
        for (int w = 0; w < width; w += stride) {
            // Loop 2: Output channels (filters)
            for (int f = 0; f < c_out; f++) {
                int32_t accum = 0;
                
                // Loop 3: Input channels
                for (int c = 0; c < c_in; c++) {
                    // Loop 4: Kernel spatial (3×3)
                    for (int ky = 0; ky < 3; ky++) {
                        for (int kx = 0; kx < 3; kx++) {
                            int h_in = h + ky;
                            int w_in = w + kx;
                            
                            if (h_in < height && w_in < width) {
                                // Load input pixel (1 byte)
                                int8_t in_val = input[h_in * width * c_in + w_in * c_in + c];
                                
                                // Load kernel weight (1 byte) 
                                int8_t w_val = kernel[ky * 3 * c_in * c_out + kx * c_in * c_out + c * c_out + f];
                                
                                // Multiply (1 byte × 1 byte → 2 bytes)
                                accum += in_val * w_val;
                            }
                        }
                    }
                }
                
                // Store result (3-4 bytes)
                output[h * width * c_out + w * c_out + f] = accum;
            }
        }
    }
}
```

**Execution Timeline Example**:
```
Cycle 1-10:   Setup (copy pointers, clear accumulators) = 10 cycles
Cycle 11-50:  Load input[0][0][0] from DDR2          = 40 cycles (memory latency)
Cycle 51-55:  Load kernel[0][0][0][0]               = 5 cycles
Cycle 56-58:  Multiply                              = 3 cycles
Cycle 59:     Add to accumulator                     = 1 cycle
Cycle 60-99:  Load next input                        = 40 cycles
...
Total for single 3×3 kernel: ~150-200 cycles
Total for full layer: millions of cycles → several milliseconds
```

---

## Stage 3: Hardware Accelerators

### Accelerator Overview

To overcome CPU bottlenecks, three specialized hardware accelerators are added:

1. **LUT Activation Accelerator** - Non-linear functions (ReLU, Sigmoid, Tanh)
2. **Matrix Multiply Accelerator (MMA)** - Optimized for INT8 convolution/FC operations
3. **ISA Extension Controller** - Custom instructions for acceleration dispatch

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LiteX SoC                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐        ┌──────────────────────────────────┐  │
│  │  VexRiscv CPU    │        │    Wishbone Bus (32-bit)         │  │
│  │                  │────────│  (CPU ↔ Accelerators)           │  │
│  │ + Custom ISA Ext │        │                                  │  │
│  └──────────────────┘        └─────────────┬────────────────────┘  │
│                                            │                       │
│                    ┌───────────────────────┼───────────────────┐   │
│                    │                       │                   │   │
│         ┌──────────▼────────────┐ ┌───────▼──────────┐ ┌──────▼─┐ │
│         │ Matrix Multiply       │ │ LUT Activation   │ │ L2 Cache│ │
│         │ Accelerator (MMA)     │ │ Accelerator      │ │ (128KB) │ │
│         │                       │ │ (LUT-based)      │ │         │ │
│         │ - 8 parallel MACs     │ │ - 64 LUT tables  │ └─────────┘ │
│         │ - INT8×INT8→INT32     │ │ - 256 entry/tbl  │             │
│         │ - 8 μops/cycle        │ │ - 1 cycle latency│             │
│         └───────────────────────┘ └──────────────────┘             │
│                   │                        │                       │
│                   └────────────┬───────────┘                       │
│                                │                                   │
│                        ┌───────▼────────┐                         │
│                        │  DDR2 + PHY    │                         │
│                        │  (128 MB)      │                         │
│                        └────────────────┘                         │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

### Accelerator 1: LUT-Based Activation Function Unit

#### Purpose
Implement non-linear activation functions with minimal latency using lookup tables (LUTs).

**Supported Activation Functions**:
- **ReLU**: max(0, x)
- **Clipped ReLU**: min(max(0, x), 6)
- **Sigmoid**: 1 / (1 + exp(-x))
- **Tanh**: (exp(2x) - 1) / (exp(2x) + 1)
- **Swish**: x × sigmoid(0.5x)

#### LUT Table Generation & Storage

**LUT Architecture**:
```
64 independent lookup tables (one per potential layer)
Each table: 256 entries × 16-bit output
Total Storage: 64 × 256 × 2 bytes = 32 KB on-chip BRAM (< 1% of total)
```

**LUT Entry Calculation (ReLU Example)**:
```python
# During hardware initialization / software configuration
def generate_relu_lut(input_bits=8, scale=1.0):
    """
    Generate ReLU LUT for INT8 input
    Input range: [-128, 127] → 256 entries
    """
    lut = []
    for i in range(256):
        # Convert unsigned index to signed INT8
        x = i - 128 if i >= 128 else i
        # Apply ReLU
        y = max(0, x)
        # Quantize output (maintain INT8 range)
        y = min(127, max(-128, y))
        lut.append(y)
    return lut

# Example output:
# Input:  -128 -127 ... -1   0   1 ... 127
# Output: 0    0   ... 0    0   1 ... 127
```

**Sigmoid LUT Generation**:
```python
import math
def generate_sigmoid_lut(input_bits=8):
    """
    Generate Sigmoid LUT for INT8 input
    Maps [-128, 127] → [0, 255] (representing [0.0, 1.0] in fixed-point)
    """
    lut = []
    for i in range(256):
        # Convert to floating-point [-4, 4]
        x = (i - 128) * 4.0 / 128.0
        # Sigmoid: 1 / (1 + exp(-x))
        sigmoid_val = 1.0 / (1.0 + math.exp(-x))
        # Quantize to [0, 255]
        quantized = int(sigmoid_val * 255)
        lut.append(quantized)
    return lut

# Example output:
# Input:  -128 (very negative)  →  0 (≈0.0)
# Input:    0 (zero)           → 128 (≈0.5)  
# Input:   127 (very positive) → 255 (≈1.0)
```

**Storage in Hardware**:
```verilog
// In Verilog/LiteX
// 64 tables × 256 entries × 16 bits = 32 KB BRAM
reg [15:0] lut_table[63:0][255:0];

// Each table configurable via CSR registers
always @(posedge clk) begin
    if (csr_lut_write_en) begin
        lut_table[csr_table_id][csr_addr] <= csr_write_data;
    end
end
```

#### Hardware Implementation

**Dataflow**:
```
CPU Issues: activat_lut r1, table_id=5, mode=relu  (custom instruction)
    │
    ├─→ Read r1 value (INT8 activation map pointer in memory)
    │
    ├─→ Load 256 bytes from memory (entire activation map)
    │
    ├─→ For each byte[i]:
    │      - Use byte as index into LUT[table_id]
    │      - Get output[i] = LUT[table_id][byte[i]]
    │      - 1 cycle per value (pipelined)
    │
    ├─→ Store 256 bytes back to memory
    │
    └─→ Return to CPU (set interrupt flag when done)
```

**Pipelining & Performance**:
```
LUT Access: 1 cycle per entry (fully pipelined)
Throughput: 256 activations / 256 cycles = 1 activation/cycle
Latency (for single image):
  - 256 activations @ 50 MHz = 256 cycles = 5.1 μs (with memory overhead)
  - Memory overhead: 256 byte load + store ≈ 10-20 μs
  - Total: ~15-25 μs

Speedup vs CPU: 
  - CPU: 256 values × 10 instructions/activation = 2560 instructions @ 50 MHz ≈ 51 μs
  - LUT Accel: 25 μs
  - Speedup: 2×
```

**CSR Register Interface**:
```
Offset  | Name           | Width | R/W | Description
--------|----------------|-------|-----|------------------------
0x0     | CTRL           | 32    | R/W | [0]=enable, [1]=mode, [2:7]=table_id
0x4     | STATUS         | 32    | R   | [0]=busy, [1]=done, [2]=error
0x8     | ADDR_IN        | 32    | R/W | Input buffer address (DDR2)
0xC     | ADDR_OUT       | 32    | R/W | Output buffer address (DDR2)
0x10    | LENGTH         | 32    | R/W | Number of bytes to process
0x14-0x54 | LUT[0-15]    | 32    | R/W | LUT data load/read (one per table)
```

**New ISA Instruction** (RV32 Custom-0 encoding):
```asm
activat_lut rd, rs1, table_id, mode
  Format: [6:0]=0011011 (custom-0), table_id[5:0], mode[3:0]
  Example: activat_lut t0, a0, 5, relu  
  Encoding: 0x0A85102B (hypothetical)

Effect:
  - rd = destination register (return value: 0=success)
  - rs1 = source address register (input/output memory location)
  - table_id = which LUT table to use [0-63]
  - mode = activation type (0=relu, 1=sigmoid, 2=tanh, 3=swish, ...)
```

**Assembly Example**:
```asm
# Activate output of convolution layer using ReLU
# Input: output activation map at a0 (256 bytes)
# Use ReLU LUT table #3

activat_lut t0, a0, 3, 0  # relu=0, table_id=3
beq t0, zero, 1f          # check error
j layer_done
1:
  # Handle error
layer_done:
  addi sp, sp, -256       # Continue to next stage
```

---

### Accelerator 2: Matrix Multiply Accelerator (MMA)

#### Purpose
Perform quantized INT8 matrix multiplications (core operation in convolution and fully-connected layers) at 8× throughput compared to CPU.

#### Architecture

**Core Design**:
```
┌────────────────────────────────────────────────────────────┐
│           Matrix Multiply Accelerator (MMA)                │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  PE (MAC) 0  │  │  PE (MAC) 1  │  │  PE (MAC) 2  │    │
│  │ INT8×INT8→   │  │ INT8×INT8→   │  │ INT8×INT8→   │    │
│  │ INT32        │  │ INT32        │  │ INT32        │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  PE (MAC) 3  │  │  PE (MAC) 4  │  │  PE (MAC) 5  │    │
│  │ INT8×INT8→   │  │ INT8×INT8→   │  │ INT8×INT8→   │    │
│  │ INT32        │  │ INT32        │  │ INT32        │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  PE (MAC) 6  │  │  PE (MAC) 7  │  │  PE (MAC) 0' │   │
│  │ INT8×INT8→   │  │ INT8×INT8→   │  │  (Reserved)  │    │
│  │ INT32        │  │ INT32        │  │              │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                            │
│  ┌──────────────────────────────────────────────────┐    │
│  │         Accumulator Register File (32-bit)       │    │
│  │  [8 accumulators for 8 parallel multiply operations] │
│  └──────────────────────────────────────────────────┘    │
│                                                            │
│  ┌──────────────────────────────────────────────────┐    │
│  │       Wishbone Interface Controller              │    │
│  │  (Memory read/write, status/control CSRs)        │    │
│  └──────────────────────────────────────────────────┘    │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

**Processing Element (PE) Specification**:

Each PE performs a single MAC (Multiply-Accumulate) operation:

```verilog
module PE(
    input clk,
    input [7:0] a,        // INT8 multiplicand (input)
    input [7:0] b,        // INT8 multiplier (weight)
    input [31:0] acc_in,  // Accumulator input
    output [31:0] acc_out // Accumulator output (acc_in + a*b)
);
    wire [15:0] mul_result;
    assign mul_result = a * b;      // 1-cycle multiply (2 cycles actual on FPGA)
    assign acc_out = acc_in + {{16{mul_result[15]}}, mul_result};  // Sign extend + add
endmodule
```

**Throughput Analysis**:
```
Parallel PEs: 8
Multiply Latency: 2 cycles (pipelined on FPGA)
Add Latency: 1 cycle (after multiply)
Total Per-MAC Latency: 3 cycles

Steady-State Throughput:
  - 8 MACs / 3 cycles = 2.67 MACs per cycle
  - At 50 MHz: 8 × 50 MHz = 400 MMAC/s (8× speedup vs CPU @ 50 MMAC/s)

BUT: Real throughput depends on memory bandwidth
  - Each operand must be fetched from memory
  - Each result must be written back
  - Bandwidth limited to 32-bit words per cycle
```

#### Data Organization in Memory

**Matrix Formats**:

**Weights Matrix (Conv Kernel)** - Row-Major Storage:
```
Layout in memory (for 3×3×3→32 convolution):
[3×3×3×32 = 864 bytes total]

kernel[3][3][3][32] stored as:
  Byte 0-31:     kernel[0][0][0][0:31]    (first 3×3 kernel, channel 0)
  Byte 32-63:    kernel[0][0][1][0:31]    (first 3×3 kernel, channel 1)
  Byte 64-95:    kernel[0][0][2][0:31]    (first 3×3 kernel, channel 2)
  Byte 96-127:   kernel[0][1][0][0:31]
  ...
  Byte 832-863:  kernel[2][2][2][0:31]    (last 3×3 kernel, last channel)
```

**Input Activation Matrix** - Channel-Last Format:
```
Input[H][W][C] stored as:
  Byte 0-2:      Input[0][0][0:2]         (pixel [0,0], all 3 channels)
  Byte 3-5:      Input[0][1][0:2]         (pixel [0,1], all 3 channels)
  Byte 6-8:      Input[0][2][0:2]
  ...
  Byte 3*32-1:   Input[0][31][0:2]        (end of row 0)
  Byte 3*32:     Input[1][0][0:2]         (start of row 1)
```

**Output Accumulator** - INT32 per Element:
```
Output[H_out][W_out][F] stored as 32-bit accumulators:
  Offset 0-3:    Output[0][0][0]          (4-byte INT32)
  Offset 4-7:    Output[0][0][1]
  ...
  Offset 4*F:    Output[0][1][0]          (next output pixel)
```

#### Matrix Multiplication Operation

**Example: 8×8 Matrix Multiply**

```c
// C[8][8] = A[8][8] × B[8][8]  (all INT8 inputs, INT32 output)

void matmul_accelerated(
    int8_t A[8][8],        // Operand A (64 bytes)
    int8_t B[8][8],        // Operand B (64 bytes)
    int32_t C[8][8],       // Output (256 bytes = 8 × 32-bit words per row)
    int n = 8              // Matrix dimension
) {
    // CPU issues 8 independent MACs per cycle
    // Accelerator completes in ceil(8*8*8 / 8) = 64 cycles (ideal, no stalls)
    
    // Actual execution:
    // Cycle 0-10:     Load A[0][0:7] (row-wise) from DDR2 = ~40 cycles
    // Cycle 11-20:    Load B[0:7][0] (column-wise) from DDR2 = ~40 cycles
    // Cycle 21-30:    Compute 8 MACs = 3 cycles pipelined
    // Cycle 31-40:    Load next column of B
    // ...
    // Cycle N:        Store C[0:7][0] to DDR2 = 10-20 cycles
}
```

#### CSR Register Interface for MMA

```
Offset  | Name            | Width | R/W | Description
--------|-----------------|-------|-----|------------------------
0x0     | CTRL            | 32    | R/W | [0]=start, [4:1]=op_type, [31:5]=reserved
0x4     | STATUS          | 32    | R   | [0]=busy, [1]=done, [2:4]=error_code
0x8     | DIM_M           | 32    | R/W | Rows of matrix A (and output C)
0xC     | DIM_N           | 32    | R/W | Columns of matrix B (and output C)
0x10    | DIM_K           | 32    | R/W | Columns of A / Rows of B (inner dimension)
0x14    | ADDR_A          | 32    | R/W | Base address of matrix A in DDR2
0x18    | ADDR_B          | 32    | R/W | Base address of matrix B in DDR2
0x1C    | ADDR_C          | 32    | R/W | Base address of matrix C in DDR2 (output)
0x20    | SCALE_OUT       | 32    | R/W | Quantization scale for output (fixed-point)
0x24    | ZERO_POINT      | 32    | R/W | Zero-point offset for output quantization
```

**Operation Types (OP_TYPE field)**:
- `0x0`: MatMul (INT8 × INT8 → INT32)
- `0x1`: MatMul + Quantize (INT8 × INT8 → INT8 with quantization)
- `0x2`: MatMul + ReLU (INT8 × INT8 → INT8 with ReLU)
- `0x3`: MatMul + Bias + ReLU (INT8 × INT8 + INT32_bias → INT8)

**New ISA Instruction**:
```asm
matmul rd, rs1, rs2, rs3, op_type
  Format: [6:0]=0011011 (custom-1), op_type[3:0]
  
  rs1 = address of matrix A
  rs2 = address of matrix B
  rs3 = address of output matrix C
  op_type = operation variant
  
  Example: matmul t0, a0, a1, a2, 2  # C = A × B + ReLU
```

#### Expected Speedup

**Convolution Layer Speedup**:
```
Operation: Conv 3×3, Input 32×32×32, Output 32×32×64

CPU (Baseline):
  - MAC count: (30×30) × 9 × 64 = 518,400 MACs
  - @ 1 MAC/cycle = 518,400 cycles @ 50 MHz = 10.4 ms
  - Actual with memory latency: ~100 ms

MMA Accelerator:
  - 8 parallel MACs per cycle
  - Effective throughput: 8 × 50 MHz = 400 MMAC/s
  - Time: 518,400 / 400M = 1.3 ms (memory optimized)
  - With DDR2 latency: ~20-30 ms
  - Speedup: 100 ms / 25 ms ≈ 4×

Fully-Connected Layer Speedup:
Operation: 1024×128 weight matrix × 1024-element vector

CPU:
  - MAC count: 1024 × 1024 = 1,048,576 MACs
  - @ 1 MAC/cycle = 1,048,576 cycles @ 50 MHz = 20.9 ms
  - Actual with memory: ~200 ms

MMA Accelerator:
  - 8 parallel MACs
  - Time: 1,048,576 / (8 × 50M) = 2.6 ms (ideal)
  - With memory: ~30-50 ms
  - Speedup: 200 ms / 40 ms = 5×
```

---

### Accelerator 3: CPU ISA Extensions & Integration

#### New Custom Instructions

**Instruction Encoding** (using RV32 custom-0 opcode):

```
Instruction Format:
┌─────────────────────────────────────────────────────────┐
│  31      27 26     22 21     17 16     12 11      7  6 0 │
│  ─────────────────────────────────────────────────────── │
│  [funct5]  [rs2]    [rs1]    [rd]     [func2] [opcode]   │
│           (accelerator select)  (dest)       (0011011)    │
│                                                         │
│  Bits [31:27] = Accelerator ID:                         │
│    0x00 = LUT Activation                                │
│    0x01 = Matrix Multiply                               │
│    0x02 = Quantization                                  │
│    0x03 = Memory Copy (DMA)                             │
│                                                         │
│  Bits [26:22] = Parameter #1 (table_id / dim_m / ...)   │
│  Bits [21:17] = Parameter #2 (mode / dim_n / ...)       │
│  Bits [16:12] = Destination register                    │
│  Bits [11:7]  = Reserved                                │
│  Bits [6:0]   = 0x1B (custom-0 opcode)                 │
└─────────────────────────────────────────────────────────┘
```

**Instruction Set**:

| Mnemonic | Encoding | Function | Latency | Interrupts |
|----------|----------|----------|---------|-----------|
| `accel_lut rd, rs1, table_id, mode` | funct5=0x00 | Lookup table activation | 1-1000 cycles | Yes |
| `accel_matmul rd, rs1, rs2, dim` | funct5=0x01 | Matrix multiply | 10-10K cycles | Yes |
| `accel_quantize rd, rs1, scale, zp` | funct5=0x02 | Quantization | 1-100 cycles | No |
| `accel_dma rd, src, dst, len` | funct5=0x03 | Memory DMA | 10-1M cycles | Yes |

#### Integration with VexRiscv

**Decode Stage Modification**:
```verilog
module VexRiscv_Custom_Decoder(
    input [31:0] instruction,
    output is_custom_instruction,
    output [4:0] accelerator_id,
    output [31:0] accel_ctrl_word
);

always @(*) begin
    if (instruction[6:0] == 7'b0011011) begin  // custom-0 opcode
        is_custom_instruction = 1'b1;
        accelerator_id = instruction[31:27];
        accel_ctrl_word = {instruction[31:12], 12'b0};
    end else begin
        is_custom_instruction = 1'b0;
        accelerator_id = 5'b0;
        accel_ctrl_word = 32'b0;
    end
end
endmodule
```

**Execute Stage Flow**:
```
CPU Instruction Fetch
    │
    ├─→ Decode: Check opcode
    │
    ├─→ If standard RV32IM: Execute normally
    │
    ├─→ If custom-0:
    │      - Extract accelerator_id from bits[31:27]
    │      - Write accel_ctrl_word to CSR_ACCEL_CTRL
    │      - Stall CPU (set wait bit)
    │      - Accelerator processes in parallel
    │      - Accelerator sets interrupt when done
    │      - CPU resumes (rd = CSR_ACCEL_RESULT)
    │
    └─→ Writeback: Store result in register
```

**Interrupt & Status Handling**:
```verilog
// Accelerator interrupt vector (configurable priority)
wire accel_irq_lut   = lut_accel.done & lut_accel.irq_en;
wire accel_irq_matmul = matmul_accel.done & matmul_accel.irq_en;
wire accel_irq_dma   = dma_accel.done & dma_accel.irq_en;

// CPU IRQ line
assign cpu_irq[7:4] = {accel_irq_matmul, accel_irq_lut, accel_irq_dma, 1'b0};

// Status register
reg [31:0] accel_status;
always @(posedge clk) begin
    accel_status <= {
        accel_irq_matmul, accel_irq_lut, accel_irq_dma,
        lut_accel.busy, matmul_accel.busy, dma_accel.busy,
        24'b0
    };
end
```

---

## System Architecture Block Diagrams

### Level 1: Complete System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NEXYS4 DDR BOARD (Artix-7 100T FPGA)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                       LiteX SoC                                       │  │
│  ├──────────────────────────────────────────────────────────────────────┤  │
│  │                                                                      │  │
│  │                   WISHBONE 32-BIT SYSTEM BUS                        │  │
│  │  ┌─────────────────────────────────────────────────────────────┐   │  │
│  │  │  (CPU ↔ L2 Cache ↔ Accelerators ↔ DDR Controller)          │   │  │
│  │  └─────────────────────────────────────────────────────────────┘   │  │
│  │                       ▲                                              │  │
│  │     ┌─────────────────┼─────────────────┬──────────────────┐        │  │
│  │     │                 │                 │                  │        │  │
│  │  ┌──▼────┐    ┌──────▼────┐    ┌──────▼────┐    ┌────────▼─┐      │  │
│  │  │ VexRI │    │  LUT Act. │    │ MatMul    │    │  CSR     │      │  │
│  │  │ scv   │    │  Accel    │    │ Accel     │    │ Bridge   │      │  │
│  │  │ CPU   │    │(256 entries)   │(8 MACs)   │    │          │      │  │
│  │  │       │    │           │    │           │    │          │      │  │
│  │  └───────┘    └───────────┘    └───────────┘    └──────────┘      │  │
│  │     │               │                 │              │              │  │
│  │  ┌──▼──┐  ┌───────▼────────┐  ┌──────▼────────┐  ┌──▼──┐          │  │
│  │  │ I$  │  │    D$          │  │   L2 Cache   │  │UART │          │  │
│  │  │16KB │  │   16 KB        │  │   128 KB     │  │Ctrl │          │  │
│  │  └─────┘  └────────────────┘  └──────────────┘  └─────┘          │  │
│  │                 │                                                  │  │
│  │                 └────────────────┬─────────────────────────────────┤  │
│  │                                  ▼                                 │  │
│  │                    ┌──────────────────────────────┐               │  │
│  │                    │    DDR2 Controller + PHY    │               │  │
│  │                    │    (LiteDRAM)                │               │  │
│  │                    └──────────────────────────────┘               │  │
│  │                                                                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                  │                                       │
└──────────────────────────────────┼───────────────────────────────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │   DDR2 SDRAM Module        │
                    │   MT47H64M16               │
                    │   128 MB (64M × 16-bit)    │
                    │                            │
                    │   Configuration:           │
                    │   - 13 row addr lines      │
                    │   - 10 col addr lines      │
                    │   - 3 bank addr lines      │
                    │   - 16-bit data bus        │
                    │   - 2 DQS differential    │
                    │   - Speed: 400 Mbps (1:4) │
                    └────────────────────────────┘
```

### Level 2: CPU & Accelerator Interface

```
┌─────────────────────────────────────────────────────────┐
│             VexRiscv CPU (50 MHz)                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Instruction: accel_lut t0, a0, table_5, relu         │
│                                                         │
│  ┌──────────────────────────────────────────────┐      │
│  │ Fetch: Load instr from I-Cache               │      │
│  └────────────────────┬─────────────────────────┘      │
│                       │                                 │
│  ┌────────────────────▼─────────────────────────┐      │
│  │ Decode: Recognize custom-0 opcode           │      │
│  │         Extract accel_id=0x00 (LUT)          │      │
│  │         Extract params: table_id=5, mode=0  │      │
│  └────────────────────┬─────────────────────────┘      │
│                       │                                 │
│  ┌────────────────────▼─────────────────────────┐      │
│  │ Execute: Stall CPU                           │      │
│  │          Write CSR_LUT_CTRL with params      │      │
│  │          LUT Accelerator reads CSR           │      │
│  │          LUT Accelerator starts operation    │      │
│  └────────────────────┬─────────────────────────┘      │
│                       │                                 │
│  ┌────────────────────▼─────────────────────────┐      │
│  │ Memory: (CPU stalled, waiting)               │      │
│  │         LUT reads input from address in a0   │      │
│  │         LUT processes 256 values (256 cycles)│      │
│  │         LUT writes output to memory          │      │
│  │         LUT interrupt signals completion     │      │
│  └────────────────────┬─────────────────────────┘      │
│                       │                                 │
│  ┌────────────────────▼─────────────────────────┐      │
│  │ Writeback: Resume CPU                        │      │
│  │            Read CSR_LUT_STATUS (result code) │      │
│  │            Store in t0                        │      │
│  │            Continue to next instruction       │      │
│  └──────────────────────────────────────────────┘      │
│                                                         │
│  Cycle Timeline:                                        │
│  Cycle 0:      Fetch
│  Cycle 1:      Decode + stall
│  Cycle 2-10:   CSR write, accel startup
│  Cycle 11-300: Accel processing (LUT 256 cycles)
│  Cycle 301:    Interrupt received, resume
│  Cycle 302:    Read status CSR
│  Cycle 303:    Writeback
│  Total: ~300 cycles vs ~51 μs (CPU = 2560 cycles)
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Level 3: Memory System Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                   L2 CACHE (128 KB, direct-mapped)              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  [Index 0]   [Index 1]   ... [Index 4095]  (4096 lines)   │  │
│  │  64 bytes    64 bytes         64 bytes     (4 words/line) │  │
│  └───────────────────────────────────────────────────────────┘  │
│         │                                          │             │
│         │ CPU Hit (1 cycle)                        │             │
│         │ Miss → Fetch from DDR2 (40+ cycles)     │             │
│         │                                          │             │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│        DDR2 MEMORY ACCESS PATTERN (for Conv Layer)              │
│                                                                 │
│  Address Range      Content           Typical Access Pattern    │
│  ─────────────────────────────────────────────────────────────  │
│  0x80000000 +      Weights/Kernels    Sequential row-wise       │
│  0x80010000        (Conv filters)     reads (good cache loc.)   │
│                                                                 │
│  0x80100000        Input activations  2D spatial locality       │
│  0x80200000        (feature maps)     (kernel footprint)       │
│                                                                 │
│  0x80400000        Output buffers     Sequential writes         │
│  0x80500000        (results)                                    │
│                                                                 │
│  DDR2 Access Timeline:                                          │
│  ├─ Tpre (precharge): 3 cycles (⚡ if same bank)                │
│  ├─ Tact (activate):  3 cycles                                  │
│  ├─ Tco (CAS latency): 2 cycles                                 │
│  ├─ Twr (write):      1 cycle                                   │
│  ├─ Tref (refresh):   ~500 cycles (transparent)                 │
│  └─ Total bank conflict: ~40-50 cycles                          │
│                                                                 │
│  Optimized Sequence (within single bank):                       │
│  ├─ Activate bank once                                          │
│  ├─ Issue multiple column reads (burst of 4)                    │
│  ├─ Precharge before different row                              │
│  └─ Achieve ~8-12 bytes per cycle throughput                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Performance Characteristics

### End-to-End Inference Latency

**Baseline (CPU Only) vs Accelerated**

```
CIFAR-10 Model (32×32 RGB → 10 classes, 5 Conv + 1 FC)

Layer               CPU Time    MMA Accel Time   Speedup
────────────────────────────────────────────────────────
Conv1 (3×3, 32)     150 ms      30 ms            5×
Conv2 (3×3, 32)     150 ms      30 ms            5×
MaxPool              20 ms       8 ms             2.5×
Conv3 (3×3, 64)     100 ms      25 ms            4×
Conv4 (3×3, 64)     100 ms      25 ms            4×
Conv5 (3×3, 128)    80 ms       20 ms            4×
FC1 (1024→128)      60 ms       15 ms            4×
FC2 (128→10)        2 ms        1 ms             2×
─────────────────────────────────────────────────
TOTAL               662 ms      154 ms           4.3×
```

**With LUT Activation Accelerator** (ReLU/Sigmoid offload):
```
Assuming 8 ReLU/Sigmoid operations per conv layer:

LUT Accel Savings:
  8 layers × 8 ReLU @ 10 μs each = 640 μs
  CPU baseline: 8 × 256 × 10 instructions/val = ~2.1 ms
  Savings: ~1.5 ms per inference = 0.2% improvement (minor)
```

### Power Consumption Estimates

| Component | Power (Idle) | Power (Active) | TDP |
|-----------|--------------|----------------|-----|
| FPGA Logic | 0.5 W | 2-3 W | 5 W |
| DDR2 SDRAM | 0.2 W | 1-2 W | 2 W |
| VexRiscv (CPU) | 0.1 W | 0.8 W | 1 W |
| LUT Accel | 0.05 W | 0.3 W | 0.4 W |
| MMA Accel | 0.05 W | 1.5 W | 2 W |
| Interconnect | 0.1 W | 0.5 W | 0.6 W |
| **Total** | **~1.0 W** | **~6-7 W** | **~11 W** |

---

## Build and Deployment

### Building the Project

```bash
# Clone repository
git clone https://github.com/YonatanGrobgeld/litex-nexys4ddr.git
cd litex-nexys4ddr

# Setup LiteX environment (Ubuntu 22.04)
bash scripts/setup_litex.sh

# Build SoC for Linux (generates RTL + constraints)
bash scripts/build.sh --rom-size 131072 --l2-size 131072

# Output: hw/build/gateware/nexys4ddr_vexriscv.v (RTL)
#         hw/build/gateware/digilent_nexys4ddr.xdc (constraints)
```

### Windows Vivado Synthesis

```bash
# On Windows machine (with Vivado installed):
# 1. Copy hw/build/gateware/* to Vivado project directory
# 2. Open Vivado → Create Project → Use existing files
# 3. Select nexys4ddr_vexriscv.v as top-level
# 4. Run synthesis & implementation
# 5. Generate bitstream → nexys4ddr_vexriscv.bit
```

### Programming the FPGA

```bash
# Connect Nexys4 DDR board via USB
# Open Vivado Hardware Manager
# Program device with nexys4ddr_vexriscv.bit
```

### Running TinyML Inference

```bash
# Connect to UART console (115200 baud)
# BIOS prompt appears
# Load model weights into DDR2 (via serial or preloaded)
# Execute inference command via UART shell
# Results printed to console
```

---

## References & Future Work

### Known Limitations

1. **DDR2 Latency**: Dominant bottleneck, partially mitigated by L2 cache
2. **Memory Bandwidth**: Limited to ~32 bits/cycle on Wishbone
3. **No DMA**: Data movement requires CPU involvement
4. **Fixed Quantization**: All layers use INT8; no mixed precision

### Future Enhancements

1. **DMA Controller**: Offload memory transfers to dedicated engine
2. **Systolic Array**: Larger (16×16) matrix multiply with higher throughput
3. **Quantization Aware Training**: Model compression before deployment
4. **Hardware Scheduling**: Better pipelining between layers
5. **DDR3/LPDDR4**: Higher bandwidth memory options
6. **Multi-core VexRiscv**: Parallel CPU execution

### References

- [LiteX Documentation](https://litex.readthedocs.io/)
- [VexRiscv CPU](https://github.com/SpinalHDL/VexRiscv)
- [TensorFlow Lite for Microcontrollers](https://www.tensorflow.org/lite/microcontrollers)
- [Xilinx Artix-7 Family](https://www.xilinx.com/products/silicon-devices/fpga/artix-7.html)

---

**Document authored**: April 13, 2026  
**Status**: Initial Release  
**Review**: Ready for implementation
