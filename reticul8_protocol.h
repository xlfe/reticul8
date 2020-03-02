/*
 * The system works as a state machine where messages to the nodes are stored by the router as pending until a success response is received
 *
 * 
 * Message ID - 2 bytes (uint16_t)
 *
 * Message to node - 2 bytes (uint16_t)
 *  bits 0-3	Message type (16 max)
 *  bits 4-7   	Node address (16 max)
 *  bits 8-13  	Port address (64 max)
 *  bits 14-15  dibit
 *
 * Normal message types
 * ID 	Message 		dibits			Extra data?
 * 0	PIN_RESET		-
 * 1 	REBOOT			-
 * 2	SYSINFO			-
 * 3 	GPIO_OUTPUT		LOW (00) / HIGH (01)
 * 4	GPIO_INPUT_WATCH	PU (00) / PD (01)	2 bytes debounce length (ms)
 * 5	PWM_DUTY		-			1 bytes duty (max 8192, i*32), 2 bytes fade_ms (uint16_t) (instant if fade_ms == 0)
 * 6	I2C			read (00) 		1 byte for SCL pin, 1 byte for read len, 1 byte dev addr, 1 byte for reg addr
 * 					  / write (01)	1 byte for SCL pin, 1 byte for data len, data (first two bytes are usually dev addr and reg addr)
 * 7	OTA_UPDATE					2 bytes (uint16_t) chunk, 2 bytes (uint16_t) data length, <var> data
 *
 *
 *
 * Message ID - 2 bytes (uint16_t)
 * 
 * Message from node - 2 bytes (uint16_t)
 *  bits 0-3	Message type (16 max)
 *  bits 4-7   	Node address (16 max)
 *  bits 8-13  	Port address (64 max)
 *  bits 14-15  dibit
 *
 * ID 	Message 		dibits			Extra data
 * 0	STARTUP
 * 1	RESULT			Success (00) / Error (01) / Unknown (11)
 * 3 	GPIO_INPUT_STATE	LOW (00) / HIGH (01)
 * 4	HEARTBEAT
 * 5	SYSINFO						System Info - 2 bytes heap usage, 2 bytes uptime
 *
 *
 * Router commands
 *
 * Ephemeral or saved (executed on system restart)
 * Command for node
 * - Command data
 * - Instant or delayed start
 * - Schedule (every_ms, count)
 * Define variable
 *  - Variable ID
 *  - Inputs
 *   - Node / Port
 *  - Boolean logic (-, AND, OR, NOT)
 *
 *  struct ast_node {
  enum { CONSTANT, ADD, SUB, ASSIGNMENT } class;
  union { int                                 value;
          struct { struct ast_node* left;
                   struct ast_node* right;  } op;
};
 *
 *
 */


