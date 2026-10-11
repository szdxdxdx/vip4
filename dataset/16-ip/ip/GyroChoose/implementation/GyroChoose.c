#include "GyroChoose.h"

void GyroChooseFun(void *p) {
    GyroChoose *pIp = (GyroChoose *)p;

    unint08 i; /* 循环用临时变量 */
    /* 确定参加工作陀螺的个数 */
    pIp->JoinTotal = 0; /* 参加定姿的陀螺个数清零 */
    pIp->gyroStatus0 = 0;

    for (i = 0; i < 9; i++) { /* 9个陀螺进行判断 */
        if (pIp->StateFlag[i] == TRUE) { /* 如果陀螺状态正常 */
            pIp->SignFlag[pIp->JoinTotal] = i; /* 统计参加定姿的陀螺螺序号 */
            pIp->JoinTotal++; /* 统计参加定姿的陀螺个数 */
            pIp->gyroStatus0 = pIp->gyroStatus0 | (1 << i);
        }
    }
    return;
}
