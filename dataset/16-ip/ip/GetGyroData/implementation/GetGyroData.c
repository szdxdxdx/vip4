#include "GetGyroData.h"


unsigned char volatile XBYTE[0xFFFF];
unsigned char volatile P1;
void Delay(int time) {}


void GetGyroDataFun(void *p) {
    GetGyroData *pIp = (GetGyroData *)p;
    unint08 si;
    unint08 tmp_ad_start;
    unint16 wd;
    unint16 tmp_hi8;
    unint16 tmp_lo4;

    /* 读EC模拟量 */
    for (si = 0; si < 9; si++) {

        P1 = (P1 & 0xF0) | pIp->chnl[si]; /* 选择通道 */

        Delay(45); /*500us*/

        /* 启动AD转换 */
        tmp_ad_start = XBYTE[pIp->ADDR_AD_START]; /* 读地址0xA000启动AD转换 */

        Delay(3); /*40us*/

        tmp_lo4 =
            XBYTE[pIp->AD_GYRO_LO4]; /* 0xA003 低4位;8位数据宽度,高4位有效*/

        tmp_hi8 = XBYTE[pIp->AD_GYRO_HI8]; /* 0xA001 高8位 */

        /* 拼12位AD转换数据 */
        wd = ((tmp_hi8 << 4) & 0x0FF0) | ((tmp_lo4 >> 4) & 0xF);

        if (pIp->type[si] == TYPE_GYRO) {
            pIp->wa[si] =
                DIVIATION_TO_FLOAT_GYRO(wd); /* GYRO 当量： 1.62760417e-3f */
        } else {
            pIp->wa[si] =
                DIVIATION_TO_FLOAT_FOG(wd); /* FOG  当量：9.765625e-4f */
        }
    }
    return;
}
