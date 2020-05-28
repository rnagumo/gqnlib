
"""Consistent Generative Query Network (a.k.a. JUMP).

(Reference)

A. Kumar et al., "Consistent Generative Query Network".
http://arxiv.org/abs/1807.02033
"""

from typing import Dict, Tuple

import torch
from torch import nn, Tensor

from .renderer import DRAWRenderer
from .representation import Simple
from .utils import nll_normal


class ConsistentGQN(nn.Module):
    """Consistent Generative Query Network (a.k.a. JUMP).

    Args:
        x_channel (int, optional): Number of channels in the observations.
        u_channel (int, optional): Number of channels in the hidden layer
            between LSTM states and the canvas (nf_to_obs).
        r_channel (int, optional): Number of channels in representation.
        e_channel (int, optional): Number of channels in the conv. layer
            mapping input images to LSTM input (nf_enc).
        d_channel (int, optional): Number of channels in the conv. layer
            mapping the canvas state to the LSTM input (nf_dec).
        h_channel (int, optional): Number of channels in LSTM layer
            (nf_to_hidden).
        z_channel (int, optional): Number of channels in the stochastic latent
            in each DRAW step (nf_z).
        stride (int, optional): Kernel size of transposed conv. layer
            (stride_to_obs).
        v_dim (int, optional): Dimension size of viewpoints.
        n_layer (int, optional): Number of recurrent layers.
        scale (int, optional): Scale of image generation process.
    """

    def __init__(self, x_channel: int = 3, u_channel: int = 128,
                 r_channel: int = 32, e_channel: int = 128,
                 d_channel: int = 128, h_channel: int = 64, z_channel: int = 3,
                 stride: int = 2, v_dim: int = 7, n_layer: int = 8,
                 scale: int = 4):
        super().__init__()

        self.representation = Simple(x_channel, v_dim)
        self.generator = DRAWRenderer(
            x_channel, u_channel, r_channel, e_channel, d_channel, h_channel,
            z_channel, stride, v_dim, n_layer, scale)

    def forward(self, x_c: Tensor, v_c: Tensor, x_q: Tensor, v_q: Tensor
                ) -> Tuple[Tensor, Tensor, Tensor]:
        """Reconstructs queried images.

        Args:
            x_c (torch.Tensor): Context images, size `(b, m, c, h, w)`.
            v_c (torch.Tensor): Context viewpoints, size `(b, m, k)`.
            x_q (torch.Tensor): Query images, size `(b, n, c, h, w)`.
            v_q (torch.Tensor): Query viewpoints, size `(b, n, k)`.

        Returns:
            canvas (torch.Tensor): Reconstructed images, size `(b, c, h, w)`.
            r_c (torch.Tensor): Representations of context, size
                `(b, r, h, w)`.
            r_q (torch.Tensor): Representations of query, size `(b, r, h, w)`.
        """

        canvas, r_c, r_q, _ = self.inference(x_c, v_c, x_q, v_q)
        return canvas, r_c, r_q

    def loss_func(self, x_c: Tensor, v_c: Tensor, x_q: Tensor, v_q: Tensor,
                  var: float = 1.0) -> Dict[str, Tensor]:
        """ELBO loss.

        Args:
            x_c (torch.Tensor): Context images, size `(b, m, c, h, w)`.
            v_c (torch.Tensor): Context viewpoints, size `(b, m, k)`.
            x_q (torch.Tensor): Query images, size `(b, n, c, h, w)`.
            v_q (torch.Tensor): Query viewpoints, size `(b, n, k)`.
            var (float, optional): Variance of observations normal dist.

        Returns:
            loss_dict (dict of [str, torch.Tensor]): Calculated losses.
        """

        *_, loss_dict = self.inference(x_c, v_c, x_q, v_q, var)
        return loss_dict

    def inference(self, x_c: Tensor, v_c: Tensor, x_q: Tensor, v_q: Tensor,
                  var: float = 1.0
                  ) -> Tuple[Tensor, Tensor, Tensor, Dict[str, Tensor]]:
        """Inference.

        Input images size should be `(b, m, c, h, w)` or `(b, c, h, w)`. The
        returned images have the same size as inputs.

        Args:
            x_c (torch.Tensor): Context images, size `(b, m, c, h, w)`.
            v_c (torch.Tensor): Context viewpoints, size `(b, m, k)`.
            x_q (torch.Tensor): Query images, size `(b, n, c, h, w)`.
            v_q (torch.Tensor): Query viewpoints, size `(b, n, k)`.
            var (float, optional): Variance of observations normal dist.

        Returns:
            canvas (torch.Tensor): Reconstructed images, size `(b, c, h, w)`.
            r_c (torch.Tensor): Representations of context, size
                `(b, r, h, w)`.
            r_q (torch.Tensor): Representations of query, size `(b, r, h, w)`.
            loss_dict (dict of [str, torch.Tensor]): Calculated losses.
        """

        # Check input shape
        original_dim = x_q.dim()
        if original_dim == 4:
            x_q = x_q.unsqueeze(1)
            v_q = v_q.unsqueeze(1)

        # Reshape: (b, m, c, h, w) -> (b*m, c, h, w)
        b, m, *x_dims = x_c.size()
        _, _, *v_dims = v_c.size()
        n = x_q.size(1)

        x_c = x_c.view(-1, *x_dims)
        v_c = v_c.view(-1, *v_dims)

        x_q = x_q.view(-1, *x_dims)
        v_q = v_q.view(-1, *v_dims)

        # Representation generated from context
        r_c = self.representation(x_c, v_c)
        _, *r_dims = r_c.size()
        r_c = r_c.view(b, m, *r_dims)
        r_c = r_c.sum(1)

        # Representation generated from query
        r_q = self.representation(x_q, v_q)
        r_q = r_q.view(b, n, *r_dims)
        r_q = r_q.sum(1)

        # Copy representations for query
        r_c = r_c.repeat(n, 1, 1, 1)
        r_q = r_q.repeat(n, 1, 1, 1)

        # Query images by v_q, i.e. reconstruct
        canvas, kl_loss = self.generator(x_q, v_q, r_c, r_q)

        # Reconstruction loss
        nll_loss = nll_normal(x_q, canvas, torch.tensor([var]), reduce=False)
        nll_loss = nll_loss.sum([1, 2, 3]).mean()

        # Returned loss
        loss_dict = {"loss": nll_loss + kl_loss, "nll_loss": nll_loss,
                     "kl_loss": kl_loss}

        # Reshape
        if original_dim == 5:
            canvas = canvas.view(b, n, *x_dims)
            r_c = r_c.view(b, n, *r_dims)
            r_q = r_q.view(b, n, *r_dims)

        return canvas, r_c, r_q, loss_dict

    def sample(self, x_c: Tensor, v_c: Tensor, v_q: Tensor) -> Tensor:
        """Samples images `x_q` by context pair `(x, v)` and query viewpoint
        `v_q`.

        Args:
            x_c (torch.Tensor): Context images, size `(b, m, c, h, w)`.
            v_c (torch.Tensor): Context viewpoints, size `(b, m, k)`.
            v_q (torch.Tensor): Query viewpoints, size `(b, k)`.

        Returns:
            canvas (torch.Tensor): Reconstructed images, size `(b, c, h, w)`.
        """

        # Reshape: (b, m, c, h, w) -> (b*m, c, h, w)
        b, m, *x_dims = x_c.size()
        _, _, *v_dims = v_c.size()

        x_c = x_c.view(-1, *x_dims)
        v_c = v_c.view(-1, *v_dims)

        # Representation generated from context.
        r = self.representation(x_c, v_c)
        _, *r_dims = r.size()
        r = r.view(b, m, *r_dims)

        # Sum over representations: (b, c, h, w)
        r = r.sum(1)

        # Sample query images
        canvas = self.generator.sample(v_q, r)

        return canvas