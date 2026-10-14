#if !defined(__IP_H__)
#define __IP_H__

#include "std_utils.h"
#include "std_bitop.h"
#include "std_tycvt.h"

#ifdef __GCC_COMPILED__
// #include "DRV_UART.h"
// #include "UartRs422.h"
#endif

typedef void            (*Fun)(void *);

#define IPCALL(IP)		(IP.fun(&IP))

#define IPCREATE(IpName, InstName, ...) IpName InstName = {.fun = IpName##Fun, __VA_ARGS__ };





#endif // __IP_H__
