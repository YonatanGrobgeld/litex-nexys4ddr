/* Standalone RISC-V program - no includes */

/* UART hardware addresses */
#define UART_BASE 0x60000000UL
#define UART_RXTX ((volatile unsigned int *)(UART_BASE + 0x00))
#define UART_TXFULL ((volatile unsigned int *)(UART_BASE + 0x04))

/* Simple UART write char */
static void uart_write(unsigned char c) {
    while (*UART_TXFULL);  /* Wait until not full */
    *UART_RXTX = (unsigned int)c;
}

/* Print string via UART */
static void uart_print(const char *s) {
    while (*s) {
        uart_write(*s++);
    }
}

/* Print unsigned 64-bit number as decimal */
static void print_u64(unsigned long long val) {
    char buf[20];
    int i = 0;
    
    if (val == 0) {
        uart_write('0');
        return;
    }
    
    while (val > 0) {
        buf[i++] = '0' + (val % 10);
        val /= 10;
    }
    
    while (i-- > 0) {
        uart_write(buf[i]);
    }
}

/* RISC-V CSR read function */
static inline unsigned long long read_csr_mcycle(void) {
    unsigned long long value;
    asm volatile ("csrr %0, mcycle" : "=r" (value));
    return value;
}

int main(void) {
    uart_print("hello\n");
    
    /* Read cycle counter before loop */
    unsigned long long cycles_start = read_csr_mcycle();
    
    /* Simple busy loop (100 iterations) */
    volatile int sum = 0;
    for (int i = 0; i < 100; i++) {
        sum += i;
    }
    
    /* Read cycle counter after loop */
    unsigned long long cycles_end = read_csr_mcycle();
    
    /* Print cycle delta */
    unsigned long long delta = cycles_end - cycles_start;
    uart_print("cycles: ");
    print_u64(delta);
    uart_print("\n");
    
    /* Loop forever */
    while (1) {
        asm volatile ("nop");
    }
    
    return 0;
}

/* Entry point - define startup code */
__attribute__((section(".text.init")))
void _start(void) {
    main();
    
    /* Hang forever */
    while (1);
}
