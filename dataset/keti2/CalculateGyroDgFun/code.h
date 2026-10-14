#if !defined(__CALCULATEGYRODG_H__)
#define __CALCULATEGYRODG_H__

/* Standalone definitions replacing unavailable generated IP.h. */
#ifndef IP_STANDALONE_TYPES
#define IP_STANDALONE_TYPES
typedef void (*Fun)(void *);
typedef unsigned char unint08;
typedef unsigned short unint16;
typedef unsigned int unint32;
typedef float float32;
#endif
#ifndef TRUE
#define TRUE 1
#define FALSE 0
#endif
#ifndef MIN
#define MIN(a,b) ((a) < (b) ? (a) : (b))
#endif
#ifndef ABS
#define ABS(a) ((a) < 0 ? -(a) : (a))
#endif

void CalculateGyroDgFun(void *p);

/* 计算陀螺三轴角速度输出 */
typedef struct __CalculateGyroDg
{
    /* 接口函数 */
    Fun     fun;
    /* 输入端口 */
 	unint08		JoinTotal;           	/* 参加定姿的陀螺个数 */
    unint08		*SignFlag; 		 	    /* 参加定姿的陀螺序号数组指针 */
    float32 	*wa;				    /* 陀螺角速度模拟量数组指针 */
    float32 	*Rtemp;		 	        /* 矩阵计算结果指针 */
    /* 输出端口 */
    float32 	W[3];				 	/* 陀螺算出的角速度 */
    /* 输入输出端口 */
    /* 状态变量 */
    /* 参数变量 */
} CalculateGyroDg;

#endif // __CALCULATEGYRODG_H__
