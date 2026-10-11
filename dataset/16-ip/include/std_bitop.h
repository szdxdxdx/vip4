/* std_mfexp.h - 规范化公共宏函数和宏表达式定义头文件 */
/* 2011.10.07, created */

#ifndef STD_MACRO_FUN_EXP_H
#define STD_MACRO_FUN_EXP_H

#include "std_basal.h"

/* CONVENIENT_FOR_LOOKUP
void ui32_mask(){} */
/* ----------------------------------------------------------------------------------------- */
/* 掩码定义 */
#define MASK_ALL8F  0xFFFFFFFFu     /* 32位掩码 */
#define MASK_HI16   0xFFFF0000u     /* 32位中的高16位 */
#define MASK_LO16   0x0000FFFFu     /* 32位中的低16位 */
#define MASK_HI08   0xFF000000u     /* 32位中的高8位 */
#define MASK_HL08   0x00FF0000u     /* 32位中的高8位 */
#define MASK_LH08   0x0000FF00u     /* 32位中的低8位 */
#define MASK_LO08   0x000000FFu     /* 32位中的低8位 */
#define MASK_LO04   0x0000000Fu     /* 32位中的低4位 */

/* CONVENIENT_FOR_LOOKUP
void bit_operation(){} */
/* ----------------------------------------------------------------------------------------- */
/* 位操作宏函数 */
/* u08 mask=0x000000FF, bp=0~7 */
/* u16 mask=0x0000FFFF, bp=0~15 */
/* u32 mask=0xFFFFFFFF, bp=0~31 */
#define BIT_GET(uv, bp, mask)           (((uv) >> (bp)) & 0x01)
#define BIT_SET(uv, bp, mask)           ((uv) = (uv) | ((0x01 << (bp)) & (mask)))
#define BIT_CLR(uv, bp, mask)           ((uv) = (uv) & ((0x01 << (bp)) ^ (mask)))

/* u8为字节数据,b8:0~7 */
#define UI08_BIT_GET(uv, bp)            ((unint08)(BIT_GET((uv), (bp), MASK_LO08)))
#define UI08_BIT_SET(uv, bp)            ((uv) = ((unint08)((uv) | ((0x01 << (bp)) & (MASK_LO08)))))
#define UI08_BIT_CLR(uv, bp)            ((uv) = ((unint08)((uv) & ((0x01 << (bp)) ^ (MASK_LO08)))))

/* u16为字节数据,b16:0~15 */
#define UI16_BIT_GET(uv, bp)            ((unint16)(BIT_GET((uv), (bp), MASK_LO16)))
#define UI16_BIT_SET(uv, bp)            ((uv) = ((unint16)((uv) | ((0x01 << (bp)) & (MASK_LO16)))))
#define UI16_BIT_CLR(uv, bp)            ((uv) = ((unint16)((uv) & ((0x01 << (bp)) ^ (MASK_LO16)))))

/* u32为字节数据,b32:0~31 */
#define UI32_BIT_GET(uv, bp)            ((unint08)(BIT_GET((uv), (bp), MASK_ALL8F)))
#define UI32_BIT_SET(uv, bp)            BIT_SET((uv), (bp), MASK_ALL8F)
#define UI32_BIT_CLR(uv, bp)            BIT_CLR((uv), (bp), MASK_ALL8F)

/* ----------------------------------------------------------------------------------------- */
/* 32位整形数中连续几位位操作宏函数 */
/* bp=0~31, 操作的起始位
   n =1-32, 操作的位数
   比如,操作 bi-b(i+1)-b(i+2),则bp=i,n=3
*/
#define UI32_BIT_MASKN(n)               (MASK_ALL8F >> (32u - (n)))

/* 32位整型数获在指定的位置取连续的几位 */
#define UI32_BIT_GETN(uv, bp, n)        (((uv) >> (bp)) & UI32_BIT_MASKN((n)))
#define UI32_BIT_GET1(uv, bp)           (((uv) >> (bp)) & 0x001u)
#define UI32_BIT_GET2(uv, bp)           (((uv) >> (bp)) & 0x003u)
#define UI32_BIT_GET3(uv, bp)           (((uv) >> (bp)) & 0x007u)
#define UI32_BIT_GET4(uv, bp)           (((uv) >> (bp)) & 0x00Fu)
#define UI32_BIT_GET5(uv, bp)           (((uv) >> (bp)) & 0x01Fu)
#define UI32_BIT_GET6(uv, bp)           (((uv) >> (bp)) & 0x03Fu)
#define UI32_BIT_GET7(uv, bp)           (((uv) >> (bp)) & 0x07Fu)
#define UI32_BIT_GET8(uv, bp)           (((uv) >> (bp)) & 0x0FFu)
#define UI32_BIT_GET10(uv, bp)          (((uv) >> (bp)) & 0x3FFu)
#define UI32_BIT_GET12(uv, bp)          (((uv) >> (bp)) & 0xFFFu)

/* 32位整型数获在指定的位置置连续的几位 */
#define UI32_BIT_SET1(uv, bp, bv)       ((uv) = ((uv) & ((0x01u << (bp)) ^ (MASK_ALL8F))) | ((bv) << (bp)))
#define UI32_BIT_SET2(uv, bp, bv)       ((uv) = ((uv) & ((0x03u << (bp)) ^ (MASK_ALL8F))) | ((bv) << (bp)))
#define UI32_BIT_SET3(uv, bp, bv)       ((uv) = ((uv) & ((0x07u << (bp)) ^ (MASK_ALL8F))) | ((bv) << (bp)))
#define UI32_BIT_SET4(uv, bp, bv)       ((uv) = ((uv) & ((0x0Fu << (bp)) ^ (MASK_ALL8F))) | ((bv) << (bp)))
#define UI32_BIT_SET5(uv, bp, bv)       ((uv) = ((uv) & ((0x1Fu << (bp)) ^ (MASK_ALL8F))) | ((bv) << (bp)))

/* ----------------------------------------------------------------------------------------- */
/* 16位整形数中连续几位位操作宏函数 */
/* 16位整型数获在指定的位置取连续的几位 */
#define UI16_BIT_GET1(uv, bp)           ((unint16)((((unint32)(uv)) >> (bp)) & 0x01))
#define UI16_BIT_GET2(uv, bp)           ((unint16)((((unint32)(uv)) >> (bp)) & 0x03))

/* 16位整型数获在指定的位置置连续的几位 */
#define UI16_BIT_SET1(uv, bp, bv)       ((uv) = (unint16)((((unint32)(uv)) & ((0x01 << (bp)) ^ (MASK_LO16))) | ((bv) << (bp))))
#define UI16_BIT_SET2(uv, bp, bv)       ((uv) = (unint16)((((unint32)(uv)) & ((0x03 << (bp)) ^ (MASK_LO16))) | ((bv) << (bp))))

/* ----------------------------------------------------------------------------------------- */
/* 32位整形数中字节操作宏函数
   32位整形数格式: HH8-HL8-LH8-LL8
   HH8: hl=0
   HL8: hl=1
   LH8: hl=2
   LL8: hl=3
*/
#define UI32_BYTE_GET(uv, hl)           (((uv) >> ((3u - (hl)) << 3u)) & 0xFFu)
#define UI32_BYTE_SET(uv, hl, byv)      ((uv) = ((uv) & ((0xFFu << ((3u - (hl)) << 3u)) ^ (MASK_ALL8F))) | ((byv) << ((3u - (hl)) << 3u)))
#define UI32_BYTE_CLR(uv, hl)           ((uv) = ((uv) & ((0xFFu << ((3u - (hl)) << 3u)) ^ (MASK_ALL8F))))

/* 设置32位无符号整型数的四个字节数 */
#define UI32_BYTE_SET_HIHI8(ui08, val)  (((ui08) & 0x00FFFFFFu) | ((val) << 24u))
#define UI32_BYTE_SET_HILO8(ui08, val)  (((ui08) & 0xFF00FFFFu) | ((val) << 16u))
#define UI32_BYTE_SET_LOHI8(ui08, val)  (((ui08) & 0xFFFF00FFu) | ((val) <<  8u))
#define UI32_BYTE_SET_LOLO8(ui08, val)  (((ui08) & 0xFFFFFF00u) | ((val)      ))


/* CONVENIENT_FOR_LOOKUP
void ui_byte_operation(){} */
/* ----------------------------------------------------------------------------------------- */
/* 提取32位无符号整型数的四个字节数,big indian */
#define UI32_HIHI8(ui32)                ((unint08)(((ui32) >> 24) & MASK_LO08))
#define UI32_HILO8(ui32)                ((unint08)(((ui32) >> 16) & MASK_LO08))
#define UI32_LOHI8(ui32)                ((unint08)(((ui32) >>  8) & MASK_LO08))
#define UI32_LOLO8(ui32)                ((unint08)(((ui32)      ) & MASK_LO08))

/* 提取32位无符号整型数的两个短整型数,big indian */
#define UI32_HI16(ui32)                 ((unint16)(((ui32) >> 16) & MASK_LO16))
#define UI32_LO16(ui32)                 ((unint16)(((ui32)      ) & MASK_LO16))

/* 提取16位无符号整型数的两个字节数,big indian */
#define UI16_HI8(ui16)                  ((unint08)(((ui16) >>  8) & MASK_LO08))
#define UI16_LO8(ui16)                  ((unint08)(((ui16)      ) & MASK_LO08))

/* 提取8位无符号整型数的4bit数,big indian */
#define UI8_HI4(ui8)                    (((ui8) >> 4) & MASK_LO04)
#define UI8_LO4(ui8)                    (((ui8)     ) & MASK_LO04)

/* 将4个字拼成64位无符号整型数,big indian */
#define UI64_MAKE16(hh, hl, lh, ll)     ((((ulong64)(hh)) << 48) | (((ulong64)(hl)) << 32) | (((ulong64)(lh)) << 16) | ((ll)))

/* 将四个字节数拼成32位无符号整型数,big indian */
#define UI32_MAKE(hh8, hl8, lh8, ll8)   ((((unint32)(hh8)) << 24) | (((unint32)(hl8)) << 16) | (((unint32)(lh8)) << 8) | ((ll8)))

/* 将两个字节数拼成16位无符号整型数,big indian */
#define UI16_MAKE(hi8, lo8)             ((unint16)((((unint32)(hi8)) << 8u) | ((unint32)(lo8))))

/* 将两个16位无符号整型数拼成32位无符号整型数,big indian */
#define UI32_MAKE16(h16, l16)           ((((unint32)(h16)) << 16) | ((unint32)(l16)))

/* 将两个字节数拼成16位无符号整型数再取高12位,big indian */
#define UI16_MAKE_HI12(hi8, lo8)        ((unint16)((((unint32)(hi8)) << 4u) | (((unint32)(lo8)) >> 4u)))

/* 将两个4位无符号整型数拼成8位无符号整型数,big indian */
#define UI08_MAKE04(h4, l4)             ((unint08)((((unint32)(h4)) << 4u) | ((unint32)(l4))))


#endif /* STD_MACRO_FUN_EXP_H */
