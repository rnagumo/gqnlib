
"""Base class for Generative Query Network."""

from typing import Tuple, Dict

from torch import nn, Tensor


class BaseGQN(nn.Module):
    """Base class for GQN models."""

    def forward(self, x_c: Tensor, v_c: Tensor, x_q: Tensor, v_q: Tensor,
                var: float = 1.0) -> Dict[str, Tensor]:
        """Returns ELBO loss in dict.

        Args:
            x_c (torch.Tensor): Context images, size `(b, m, c, h, w)`.
            v_c (torch.Tensor): Context viewpoints, size `(b, m, k)`.
            x_q (torch.Tensor): Query images, size `(b, n, c, h, w)`.
            v_q (torch.Tensor): Query viewpoints, size `(b, n, k)`.
            var (float, optional): Variance of observations normal dist.

        Returns:
            loss_dict (dict of [str, torch.Tensor]): Dict of calculated losses
                with size `(b, n)`.
        """

        _, loss_dict = self.inference(x_c, v_c, x_q, v_q, var)
        return loss_dict

    def loss_func(self, x_c: Tensor, v_c: Tensor, x_q: Tensor, v_q: Tensor,
                  var: float = 1.0) -> Dict[str, Tensor]:
        """Returns averaged ELBO loss with separated nll and kl losses in dict.

        Args:
            x_c (torch.Tensor): Context images, size `(b, m, c, h, w)`.
            v_c (torch.Tensor): Context viewpoints, size `(b, m, k)`.
            x_q (torch.Tensor): Query images, size `(b, n, c, h, w)`.
            v_q (torch.Tensor): Query viewpoints, size `(b, n, k)`.
            var (float, optional): Variance of observations normal dist.

        Returns:
            loss_dict (dict of [str, torch.Tensor]): Dict of calculated losses
                with size `(1,)`.
        """

        _, loss_dict = self.inference(x_c, v_c, x_q, v_q, var)

        # Mean for batch
        for key, value in loss_dict.items():
            loss_dict[key] = value.mean()

        return loss_dict

    def reconstruct(self, x_c: Tensor, v_c: Tensor, x_q: Tensor, v_q: Tensor
                    ) -> Tensor:
        """Reconstructs given query images with contexts.

        Args:
            x_c (torch.Tensor): Context images, size `(b, m, c, h, w)`.
            v_c (torch.Tensor): Context viewpoints, size `(b, m, k)`.
            x_q (torch.Tensor): Query images, size `(b, n, c, h, w)`.
            v_q (torch.Tensor): Query viewpoints, size `(b, n, k)`.

        Returns:
            canvas (torch.Tensor): Reconstructed images..
        """

        (canvas, *_), _ = self.inference(x_c, v_c, x_q, v_q)
        return canvas

    def inference(self, x_c: Tensor, v_c: Tensor, x_q: Tensor, v_q: Tensor,
                  var: float = 1.0
                  ) -> Tuple[Tuple[Tensor, ...], Dict[str, Tensor]]:
        """Inferences with context and target data to calculate ELBO loss.

        **Caution**: Returned `loss_dict` must include `loss` key.

        Args:
            x_c (torch.Tensor): Context images, size `(b, m, c, h, w)`.
            v_c (torch.Tensor): Context viewpoints, size `(b, m, k)`.
            x_q (torch.Tensor): Query images, size `(b, n, c, h, w)`.
            v_q (torch.Tensor): Query viewpoints, size `(b, n, k)`.
            var (float, optional): Variance of observations normal dist.

        Returns:
            data (tuple of torch.Tensor): Tuple of inferenced data. Size of
                each tensor is `(b, n, c, h, w)`.
            loss_dict (dict of [str, torch.Tensor]): Dict of calculated losses
                with size `(b, n)`.
        """

        raise NotImplementedError
