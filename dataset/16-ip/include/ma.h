/* ma.h - 宏定义源文件 */
/* 版权 2009-2010 北京控制工程研究所软件中心 */
/* 2009.09.04, dujw created */

#include "pth_basal.h"

#define __DEBUG__  0
/* --------模式字定义-------- */

#define TRUE   0xEB
#define FALSE  0x00

#ifndef  TRUE32
#define  TRUE32 0x90  /* 返回布尔真定义 */
#endif 
#ifndef  FALSE32
#define  FALSE32 0x00  /* 返回布尔假定义 */
#endif
//#define  FLT32_ZERO                 1.0E-6
                                   
#define SAM_DAMP    0x00    /* SAM速率阻尼方式 */
#define SAM_PITCH   0x11    /* SAM俯仰搜索方式 */
#define SAM_ROLL    0x22    /* SAM滚动搜索方式 */
#define SAM_CRUISE  0x33    /* SAM巡航方式 */
#define NOCTRL      0x44    /* 不控 */



/* -------- 推力器AB分支选择 -------- */
#define TBS_A  0x00     /* 选择A分支 */
#define TBS_B  0x33     /* 选择B分支 */
#define TBS_AB 0xCC     /* 选择AB分支 */

/************************与太敏接口*************************************/
#define ADDR_STATE      0xE000        /* SP */
#define PS_C000         0xC000        /* 太敏等电源状态 */
//#define ADDR_AD_START  0xA000       /* 读地址0xA000启动AD转换 */
#define AD_SS_GYRO_LO4  0xA003        /* A/D转换后的12位数据,0xA003的D[7:4]（低4位） */
#define AD_SS_GYRO_HI8  0xA001        /* A/D转换后的12位数据,0xA001的D[7:0]（高8位） */

/* --------三取二分区定义-------- */
#define FST_FLGMODE        ((volatile unint08 xdata *)0x7D00)
#define FST_BIAS_WXRO      ((volatile float32 xdata *)0x7D18)
#define FST_BIAS_WYPI      ((volatile float32 xdata *)0x7D1C)
#define FST_FT_HEALTHWORD  ((volatile unint32 xdata *)0x7D24)

#define SND_FLGMODE        ((volatile unint08 xdata *)0x7E54)
#define SND_BIAS_WXRO      ((volatile float32 xdata *)0x7E6C)
#define SND_BIAS_WYPI      ((volatile float32 xdata *)0x7E70)
#define SND_FT_HEALTHWORD  ((volatile unint32 xdata *)0x7E78)

#define TRD_FLGMODE        ((volatile unint08 xdata *)0x7FA8)
#define TRD_BIAS_WXRO      ((volatile float32 xdata *)0x7FC0)
#define TRD_BIAS_WYPI      ((volatile float32 xdata *)0x7FC4)
#define TRD_FT_HEALTHWORD  ((volatile unint32 xdata *)0x7FCC)


#define TR32_FLGMODE()        Tr32Uint08(FST_FLGMODE, SND_FLGMODE, TRD_FLGMODE)
#define TR32_BIAS_WXRO()      Tr32Float(FST_BIAS_WXRO, SND_BIAS_WXRO, TRD_BIAS_WXRO)
#define TR32_BIAS_WYPI()      Tr32Float(FST_BIAS_WYPI, SND_BIAS_WYPI, TRD_BIAS_WYPI)
#define TR32_FT_HEALTHWORD()  Tr32Uint(FST_FT_HEALTHWORD, SND_FT_HEALTHWORD, TRD_FT_HEALTHWORD)

#define TR32_FLGMODE_VALUE(x)    TR32_VALUE(FST_FLGMODE, SND_FLGMODE, TRD_FLGMODE, (x))
#define TR32_BIAS_WXRO_VALUE(x)  TR32_VALUE(FST_BIAS_WXRO, SND_BIAS_WXRO, TRD_BIAS_WXRO, (x))
#define TR32_BIAS_WYPI_VALUE(x)  TR32_VALUE(FST_BIAS_WYPI, SND_BIAS_WYPI, TRD_BIAS_WYPI, (x))

#define TR16_VALUE(pA,pB,pC,nval)   {*(pA) = (nval); *(pB) = (nval); *(pC) = (nval);}
#define TR32_VALUE(pA,pB,pC,nval)   {*(pA) = (nval); *(pB) = (nval); *(pC) = (nval);}

#define WR_FST_FT_HEALTHWORD(x)    {*(FST_FT_HEALTHWORD) = (x);}
#define WR_SND_FT_HEALTHWORD(x)    {*(SND_FT_HEALTHWORD) = (x);}
#define WR_TRD_FT_HEALTHWORD(x)    {*(TRD_FT_HEALTHWORD) = (x);}

/* -------- 单精度浮点型与偏移二进制码之间转换函数 -------- */

/* 偏移二进制转换为单精度浮点数 */
float32 DiviationToFloat(unint32 input, unint32 mask, unint32 offset, float64 LSB)
{
    float64 fresult; /* 局部变量 */

    fresult= ((siint32)((input & mask) - offset))*LSB;  /*LSB为最小当量 */
    
    return(float32 )fresult;
}


/* 太阳敏感器输入数据转换 */
#define DIVIATION_TO_FLOAT_DSS(x)   DiviationToFloat((x), 0xFFF, 0x800, 2.44140625e-3f)  /*  5/2048 -5~5° */   
#define DIVIATION_TO_FLOAT_GYRO(x)  DiviationToFloat((x), 0xFFF, 0x800, 1.62760417e-3f)  /*  5/3072 -2.5~2.5°/S  */ 
#define DIVIATION_TO_FLOAT_FOG(x)   DiviationToFloat((x), 0xFFF, 0x800, 9.765625e-4f)    /*    1/1024° */ 

#define ABS(a)     (((a) > 0) ? (a) : -(a))
#define MIN(a, b)  (((a) > (b)) ? (b) : (a))
/* RAM地址有效性判断 */
//#define RAM_VALIDATE(addr)      ((0x0  <= (addr)) && ((addr) <= 0x7FFF))




