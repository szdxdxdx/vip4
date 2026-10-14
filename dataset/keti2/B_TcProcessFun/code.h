#if !defined(__B_TCPROCESS_H__)
#define __B_TCPROCESS_H__

/* 本地基础类型，不依赖外部 IP.h。 */
typedef void (*Fun)(void *);
typedef unsigned char unint08;

/* 模式值依据本组件 Formal Model/contractscontract.txt 恢复。 */
#define SAM_DAMP   0x00
#define SAM_CRUISE 0x33
#define NOCTRL     0x44

void B_TcProcessFun(void *p);

/* 指令处理 */
typedef struct __B_TcProcess
{
    /* 接口函数 */
    Fun     fun;
    /* 输入端口 */
    unint08* tcaData;
    /* 输出端口 */
    unint08* workMode;
    /* 输入输出端口 */
    /* 状态变量 */
    /* 参数变量 */
} B_TcProcess;

#endif // __B_TCPROCESS_H__
